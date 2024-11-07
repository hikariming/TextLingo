from datetime import datetime
from mongoengine import Document, StringField, ReferenceField, DateTimeField

class UserGrammar(Document):
    """用户收藏的语法点
    user_id: 用户ID
    name: 语法点名称
    explanation: 语法解释
    source_segment_id: 来源段落ID（可选）
    """
    user_id = StringField(required=True)
    name = StringField(required=True)
    explanation = StringField(required=True)
    source_segment_id = StringField()  # 可选，记录语法点来源
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'user_grammars',
        'indexes': [
            'user_id',
            ('user_id', 'name'),  # 复合索引，防止用户重复收藏
            'created_at'
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(UserGrammar, self).save(*args, **kwargs)

    def to_dict(self):
        return {
            "_id": str(self.id),
            "user_id": self.user_id,
            "name": self.name,
            "explanation": self.explanation,
            "source_segment_id": self.source_segment_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }