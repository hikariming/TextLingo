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
    material_id = StringField(required=True)  # 只存储 ID
    original = StringField(required=True)  # 原文内容
    translation = StringField(default="")  # 翻译内容，改为默认空字符串
    is_new_paragraph = BooleanField(default=False)  # 是否新段落标记
    grammar = ListField(StringField())  # 语法解释列表
    vocabulary = ListField(EmbeddedDocumentField(VocabularyItem))  # 词汇列表
    
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
            "id": str(self.id),
            "material_id": self.material_id,
            "original": self.original,
            "translation": self.translation,
            "is_new_paragraph": self.is_new_paragraph,
            "grammar": self.grammar,
            "vocabulary": [{
                "word": v.word,
                "reading": v.reading,
                "meaning": v.meaning
            } for v in self.vocabulary],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }