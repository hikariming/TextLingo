from bson import ObjectId
from openai import AsyncOpenAI
from typing import List
from models.material import Material
from models.material_segment import MaterialSegment, VocabularyItem
from datetime import datetime
import yaml
import os
import json

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

    def _log_to_file(self, material_id: str, step: str, content: dict):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{material_id}_{step}_{timestamp}.json"
        filepath = os.path.join(self.log_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    async def translate_material(self, material_id: str):
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
                {"role": "system", "content": """Analyze the grammar points in the following text. 
                For Japanese text, explain key grammar patterns, particles, and sentence structures.
                For English text, explain sentence structures, tenses, and phrases.
                Return a list of explanations, each focusing on one grammar point."""},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.split('\n')

    async def _analyze_vocabulary(self, text: str) -> List[dict]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": """Identify important vocabulary in the text. For each word:
                - For Japanese: provide word, reading (in hiragana), and meaning
                - For English: provide word and meaning
                Format: word|reading|meaning (reading can be empty for English words)"""},
                {"role": "user", "content": text}
            ]
        )
        vocab_lines = response.choices[0].message.content.split('\n')
        vocab_items = []
        for line in vocab_lines:
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    vocab_items.append({
                        "word": parts[0].strip(),
                        "reading": parts[1].strip() if len(parts) > 2 else "",
                        "meaning": parts[-1].strip()
                    })
        return vocab_items