from bson import ObjectId
from openai import AsyncOpenAI, OpenAI
from typing import List
from models.material import Material
from models.material_segment import MaterialSegment, VocabularyItem, GrammarItem
from datetime import datetime
import yaml
import os
import json
import json_repair
import asyncio
from functools import wraps
import threading
import re
from services.setting_service import SettingService

def ensure_event_loop():
    """确保当前线程有事件循环"""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        # 如果当前线程没有事件循环，创建一个新的
        asyncio.set_event_loop(asyncio.new_event_loop())

def with_event_loop(f):
    """装饰器：确保异步函数在事件循环中运行"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 如果当前线程没有事件循环，创建一个新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            # 清理事件循环
            if not loop.is_closed():
                loop.close()
    return wrapper

class TranslationService:
    def __init__(self):
        # 从数据库获取配置
        config = SettingService.get_llm_config()
        
        self.client = AsyncOpenAI(
            api_key=config['llm_api_key'],
            base_url=config['llm_base_url']
        )
        self.model = config['llm_model']
        
        print(f"LLM API Key: {config['llm_api_key']}")
        print(f"LLM Base URL: {config['llm_base_url']}")
        print(f"LLM Model: {self.model}")
        
        # 创建日志目录
        self.log_dir = os.path.join(os.getcwd(), 'data', 'step3_ai_exp')
        os.makedirs(self.log_dir, exist_ok=True)

        self._loop = None

    def _get_loop(self):
        """获取当前线程的事件循环"""
        if self._loop is None or self._loop.is_closed():
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def _log_to_file(self, material_id: str, log_type: str, content: dict):
        """
        统一的日志记录方法
        log_type: 'translation' 或 'error' 或 'response'
        """
        # 根据日志类型确定文件名
        filename = f"{material_id}_{log_type}.json"
        filepath = os.path.join(self.log_dir, filename)
        
        # 读取现有日志（如果存在）
        existing_logs = []
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    existing_logs = json_repair.loads(f.read())
                except Exception:
                    existing_logs = []
        
        # 添加时间戳到内容中
        content['timestamp'] = datetime.now().isoformat()
        
        # 将新日志添加到列表中
        existing_logs.append(content)
        
        # 写入更新后的日志
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(existing_logs, f, ensure_ascii=False, indent=2)

    def translate_material(self, material_id: str):
        """同步版本的翻译方法"""
        # 使用 with_event_loop 装饰器的逻辑来确保正确的事件循环处理
        ensure_event_loop()
        loop = asyncio.get_event_loop()
        try:
            return loop.run_until_complete(self._async_translate_material(material_id))
        except Exception as e:
            print(f"Translation error: {str(e)}")  # 添加错误日志
            raise
        finally:
            # 不要关闭事件循环，只清理当前任务
            loop.stop()
            loop.run_forever()

    async def _async_translate_material(self, material_id: str):
        """异步翻译方法"""
        try:
            if not ObjectId.is_valid(material_id):
                raise ValueError("Invalid material ID format")
            
            material_obj_id = ObjectId(material_id)
            
            # 添加更多调试信息
            print(f"Starting translation for material: {material_id}")
            
            material = await asyncio.to_thread(
                lambda: Material.objects(id=material_obj_id).modify(
                    set__translation_status="processing",
                    new=True,
                    upsert=False
                )
            )
            
            print(f"Material retrieved and status updated")
            
            # 获取段落也使用 asyncio.to_thread
            segments = await asyncio.to_thread(
                lambda: list(MaterialSegment.objects(material_id=str(material_obj_id)))
            )
            
            print(f"Found {len(segments)} segments to translate")
            
            for segment in segments:
                try:
                    # 翻译原文
                    translation = await self._translate_text(segment.original, material.target_language)
                    update_data = {"translation": translation}
                    
                    # 如果开启深度讲解，添加语法和词汇解释
                    if material.enable_deep_explanation:
                        grammar_points = await self._analyze_grammar(segment.original)
                        vocabulary_items = await self._analyze_vocabulary(segment.original)
                        
                        # 创建 GrammarItem 和 VocabularyItem 对象
                        grammar_items = [
                            GrammarItem(
                                name=point['name'],
                                explanation=point['explanation']
                            ) for point in grammar_points
                        ]
                        
                        vocab_items = [
                            VocabularyItem(
                                word=item['word'],
                                reading=item.get('reading', ''),  # 使用 get 方法处理可选字段
                                meaning=item['meaning']
                            ) for item in vocabulary_items
                        ]
                        
                        # 更新数据
                        update_data.update({
                            "grammar": grammar_items,
                            "vocabulary": vocab_items
                        })
                    
                    # 使用 modify 方法进行原子更新
                    await asyncio.to_thread(
                        lambda: MaterialSegment.objects(id=segment.id).modify(
                            **{f"set__{k}": v for k, v in update_data.items()},
                            upsert=False
                        )
                    )
                    
                    self._log_to_file("gptlog", 'translation', {
                        'segment_id': str(segment.id),
                        'original': segment.original,
                        'translation': translation
                    })
                    
                except Exception as e:
                    self._log_to_file("gptlog", 'error', {
                        'segment_id': str(segment.id),
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    raise e

            # 最终状态更新
            Material.objects(id=material_obj_id).modify(
                set__translation_status="completed",
                set__status="translated",
                upsert=False
            )

        except Exception as e:
            self._log_to_file("gptlog", 'error', {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            Material.objects(id=material_obj_id).modify(
                set__translation_status="failed",
                set__status="translation_failed",
                upsert=False
            )
            raise e

    async def _translate_text(self, text: str, target_language: str) -> str:
        print(f"\n[Translation] Input text: {text[:100]}...")
        print(f"[Translation] Target language: {target_language}")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following text to {target_language}. Maintain the original meaning and style.在输出中，不要有除了原文翻译外的其他元素。"},
                {"role": "user", "content": text}
            ]
        )
        translated_text = response.choices[0].message.content
        
        # 记录原始响应
        self._log_to_file("gptlog", 'response', {
            'type': 'translation',
            'input': text,
            'target_language': target_language,
            'raw_response': response.model_dump()
        })
        
        print(f"[Translation] Result: {translated_text[:100]}...")
        return translated_text

    async def _analyze_grammar(self, text: str) -> List[GrammarItem]:
        print(f"\n[Grammar Analysis] Input text: {text[:100]}...")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """请分析以下文本中的语法点。
                对于每个语法点，请按照以下JSON格式返回：
                {
                    "grammar_points": [
                        {
                            "name": "语法点名称",
                            "explanation": "详细解释，使用{target_language}进行讲解"
                        }
                    ]
                }
                
                要求：
                - 对日语文本：解释重要语法模式、助词和句子结构，按照日语能力考的语法点分类
                - 对英语文本：解释句子结构、时态和短语，按照托福雅思的语法点分类
                - 每个语法点需包含名称和解释两个字段
                - 确保返回的是合法的JSON格式，用```json ```包裹
                - 讲解（explanation字段）使用的语言为简体中文
                
                示例输入：
                今から映画を見に行きます。
                
                示例输出：
                ```json
                {
                    "grammar_points": [
                        {
                            "name": "时间点语法「今から」",
                            "explanation": "「今から」表示"从现在开始"的意思，用于表示某个动作或事件的起始时间点。常用于描述即将发生的事情。"
                        },
                        {
                            "name": "目的助词「〜に」",
                            "explanation": "在「見に行く」中，「に」用作目的助词，表示动作的目的。这是一个常见的日语语法结构，用于表达"去做某事"。"
                        }
                    ]
                }
                ```"""},
                {"role": "user", "content": text}
            ]
        )
        
        # 从响应中提取JSON内容
        content = response.choices[0].message.content
        
        # 记录原始响应
        self._log_to_file("gptlog", 'response', {
            'type': 'grammar_analysis',
            'input': text,
            'raw_response': response.model_dump(),
            'content': content  # 添加content内容到日志
        })
        
        # 使用正则表达式提取JSON部分
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            grammar_data = json_repair.loads(json_match.group(1))
        else:
            # 如果没有找到JSON格式，尝试直接解析整个内容
            grammar_data = json_repair.loads(content)
            
        print(f"[Grammar Analysis] Found {len(grammar_data['grammar_points'])} grammar points")
        return grammar_data['grammar_points']

    async def _analyze_vocabulary(self, text: str) -> List[dict]:
        print(f"\n[Vocabulary Analysis] Input text: {text[:100]}...")
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """请识别用户输入的文本中重要词汇。
                请按照以下JSON格式返回：
                {
                    "vocabulary_items": [
                        {
                            "word": "单词/词组原文",
                            "reading": "读音（假名）如果不是日语词汇，请留空",
                            "meaning": "词义解释"
                        }
                    ]
                }
                
                要求：
                - 对日语词汇提供单词、假名读音和中文含义
                - 对英语词汇：提供单词和中文含义（reading字段留空）
                - 确保返回的是合法的JSON格式，用```json ```包裹
                - 讲解使用的语言为 {target_language}，不要使用其他语言讲解，不然学习者会会看不懂 """},
                {"role": "user", "content": f"你需要分析的文本是括号中内容：【【【 {text} 】】】"}
            ]
        )
        
        # 从响应中提取JSON内容
        content = response.choices[0].message.content
        
        # 记录原始响应
        self._log_to_file("gptlog", 'response', {
            'type': 'vocabulary_analysis',
            'input': text,
            'raw_response': response.model_dump(),
            'content': content  # 添加content内容到日志
        })
        
        # 使用正则表达式提取JSON部分
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            vocab_data = json_repair.loads(json_match.group(1))
        else:
            # 如果没有找到JSON格式，尝试直接解析整个内容
            vocab_data = json_repair.loads(content)
            
        print(f"[Vocabulary Analysis] Found {len(vocab_data['vocabulary_items'])} vocabulary items")
        return vocab_data['vocabulary_items']

    @staticmethod
    def test_llm_connection():
        """测试LLM API连接是否正常"""
        try:
            config = SettingService.get_llm_config()
            client = OpenAI(
                api_key=config['llm_api_key'],
                base_url=config['llm_base_url']
            )
            
            # 直接发送同步请求
            response = client.chat.completions.create(
                model=config['llm_model'],
                messages=[
                    {"role": "user", "content": "Hello, this is a test message.return yes if you can understand me."}
                ]
            )
            
            return {
                "status": "success",
                "message": "LLM API连接测试成功",
                "model": config['llm_model'],
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"LLM API连接测试失败: {str(e)}",
                "error": str(e)
            }