from datetime import datetime
from mongoengine import (
    Document, 
    StringField, 
    ListField, 
    EmbeddedDocument, 
    EmbeddedDocumentField,
    BooleanField,
    ReferenceField,
    DateTimeField
)

class GrammarItem(EmbeddedDocument):
    """语法项
    name: 语法点名称
    explanation: 语法解释
    """
    name = StringField(required=True)
    explanation = StringField(required=True)

class VocabularyItem(EmbeddedDocument):
    """词汇项
    word: 单词/词组原文
    reading: 读音（假名等）
    meaning: 含义解释
    """
    word = StringField(required=True)
    reading = StringField()  # 可选，因为英文材料可能不需要读音
    meaning = StringField(required=True)

class MaterialSegment(Document):
    """材料分段
    material_id: 关联的材料ID
    original: 原文内容
    translation: 翻译内容
    is_new_paragraph: 是否新段落
    grammar: 语法解释列表
    vocabulary: 词汇解释列表
    """
    material_id = StringField(required=True)  # Keep as StringField but ensure it's properly handled
    original = StringField(required=True)  # 原文内容
    translation = StringField(default="")  # 翻译内容，改为默认空字符串
    is_new_paragraph = BooleanField(default=False)  # 是否新段落标记
    grammar = ListField(EmbeddedDocumentField(GrammarItem))  # 修改为使用 GrammarItem
    vocabulary = ListField(EmbeddedDocumentField(VocabularyItem))
    
    # 时间戳
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'material_segments',
        'indexes': [
            'material_id',  # 为material_id字段创建索引
            'created_at'
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(MaterialSegment, self).save(*args, **kwargs)

    def to_dict(self):
        return {
            "_id": str(self.id),  # Changed from "id" to "_id" to match MongoDB convention
            "material_id": self.material_id,
            "original": self.original,
            "translation": self.translation,
            "is_new_paragraph": self.is_new_paragraph,
            "grammar": [{
                "name": g.name,
                "explanation": g.explanation
            } for g in self.grammar],
            "vocabulary": [{
                "word": v.word,
                "reading": v.reading,
                "meaning": v.meaning
            } for v in self.vocabulary],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }