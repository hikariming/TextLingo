from datetime import datetime
from mongoengine import Document, StringField, ReferenceField, DateTimeField

class UserVocabulary(Document):
    """用户收藏的词汇
    user_id: 用户ID
    word: 单词/词组原文
    reading: 读音
    meaning: 含义解释
    source_segment_id: 来源段落ID（可选）
    """
    user_id = StringField(required=True)
    word = StringField(required=True)
    reading = StringField()
    meaning = StringField(required=True)
    source_segment_id = StringField()  # 可选，记录单词来源
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'user_vocabularies',
        'indexes': [
            'user_id',
            ('user_id', 'word'),  # 复合索引，防止用户重复收藏
            'created_at'
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(UserVocabulary, self).save(*args, **kwargs)

    def to_dict(self):
        return {
            "_id": str(self.id),
            "user_id": self.user_id,
            "word": self.word,
            "reading": self.reading,
            "meaning": self.meaning,
            "source_segment_id": self.source_segment_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }