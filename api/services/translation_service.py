from bson import ObjectId
from openai import AsyncOpenAI
from typing import List
from models.material import Material
from models.material_segment import MaterialSegment, VocabularyItem
from datetime import datetime
import yaml
import os
import json
import asyncio
from functools import wraps
import threading

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
        # 读取配置文件
        with open('config.yml', 'r') as file:
            config = yaml.safe_load(file)
        
        self.client = AsyncOpenAI(
            api_key=config['llm_api_key'],
            base_url=config['llm_base_url']
        )
        self.model = config['llm_model']
        
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

    def _log_to_file(self, material_id: str, step: str, content: dict):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{material_id}_{step}_{timestamp}.json"
        filepath = os.path.join(self.log_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    def translate_material(self, material_id: str):
        """同步版本的翻译方法"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._async_translate_material(material_id))
        finally:
            loop.close()

    async def _async_translate_material(self, material_id: str):
        """原来的 translate_material 方法的内容移到这里"""
        try:
            if not ObjectId.is_valid(material_id):
                raise ValueError("Invalid material ID format")
            
            material_obj_id = ObjectId(material_id)
            
            # 使用 modify 直接更新文档，并返回更新后的文档
            material = Material.objects(id=material_obj_id).modify(
                set__translation_status="processing",
                new=True,  # 返回更新后的文档
                upsert=False  # 如果文档不存在，不创建新文档
            )
            
            # 添加详细的调试信息
            print(f"Material ID: {material_id}")
            print(f"Material Object ID: {material_obj_id}")
            print(f"Retrieved Material: {material.to_dict() if material else None}")
            
            if not material:
                raise ValueError(f"Material not found with id: {material_id}")

            segments = MaterialSegment.objects(material_id=str(material_obj_id))
            
            for segment in segments:
                try:
                    # 翻译原文
                    translation = await self._translate_text(segment.original, material.target_language)
                    self._log_to_file(material_id, 'translation', {
                        'segment_id': str(segment.id),
                        'original': segment.original,
                        'translation': translation
                    })
                    
                    update_data = {"translation": translation}
                    
                    # 如果开启深度讲解，添加语法和词汇解释
                    if material.enable_deep_explanation:
                        grammar_points = await self._analyze_grammar(segment.original)
                        self._log_to_file(material_id, 'grammar', {
                            'segment_id': str(segment.id),
                            'original': segment.original,
                            'grammar_points': grammar_points
                        })
                        
                        vocabulary_items = await self._analyze_vocabulary(segment.original)
                        self._log_to_file(material_id, 'vocabulary', {
                            'segment_id': str(segment.id),
                            'original': segment.original,
                            'vocabulary_items': vocabulary_items
                        })
                        
                        update_data.update({
                            "grammar": grammar_points,
                            "vocabulary": [
                                VocabularyItem(
                                    word=item["word"],
                                    reading=item.get("reading", ""),
                                    meaning=item["meaning"]
                                ) for item in vocabulary_items
                            ]
                        })

                    segment.update(**update_data)
                    
                except Exception as e:
                    self._log_to_file(material_id, 'error', {
                        'segment_id': str(segment.id),
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    raise e

            # 最终状态更新
            Material.objects(id=material_obj_id).modify(
                set__translation_status="completed",
                upsert=False
            )

        except Exception as e:
            self._log_to_file(material_id, 'error', {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            Material.objects(id=material_obj_id).modify(
                set__translation_status="failed",
                upsert=False
            )
            raise e

    async def _translate_text(self, text: str, target_language: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"You are a professional translator. Translate the following text to {target_language}. Maintain the original meaning and style."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content

    async def _analyze_grammar(self, text: str) -> List[str]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """请分析以下文本中的语法点。
                对于每个语法点，请按照以下JSON格式返回：
                {
                    "grammar_points": [
                        {
                            "name": "语法点名称",
                            "explanation": "详细解释"
                        }
                    ]
                }
                
                要求：
                - 对日语文本：解释重要语法模式、助词和句子结构，按照日语能力考的语法点分类
                - 对英语文本：解释句子结构、时态和短语，按照托福雅思的语法点分类
                - 每个语法点需包含名称和解释两个字段
                - 确保返回的是合法的JSON格式"""},
                {"role": "user", "content": text}
            ]
        )
        # 解析JSON响应
        grammar_data = json.loads(response.choices[0].message.content)
        return [GrammarItem(name=item["name"], explanation=item["explanation"]) 
                for item in grammar_data["grammar_points"]]

    async def _analyze_vocabulary(self, text: str) -> List[dict]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """请识别文本中的重要词汇。
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
                - 对日语词汇：提供单词、假名读音和中文含义
                - 对英语词汇：提供单词和中文含义（reading字段留空）
                - 确保返回的是合法的JSON格式"""},
                {"role": "user", "content": text}
            ]
        )
        # 解析JSON响应
        vocab_data = json.loads(response.choices[0].message.content)
        return [VocabularyItem(
                    word=item["word"],
                    reading=item.get("reading", ""),
                    meaning=item["meaning"]
                ) for item in vocab_data["vocabulary_items"]]