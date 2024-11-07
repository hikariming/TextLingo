from datetime import datetime
from mongoengine import Document, StringField, DateTimeField

class UserVocabulary(Document):
    """用户收藏的词汇
    word: 单词/词组原文
    reading: 读音
    meaning: 含义解释
    source_segment_id: 来源段落ID（可选）
    """
    word = StringField(required=True)
    reading = StringField()
    meaning = StringField(required=True)
    source_segment_id = StringField()  # 可选，记录单词来源
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'user_vocabularies',
        'indexes': [
            'word',  # 单词索引
            'created_at'
        ]
    }

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(UserVocabulary, self).save(*args, **kwargs)

    def to_dict(self):
        return {
            "_id": str(self.id),
            "word": self.word,
            "reading": self.reading,
            "meaning": self.meaning,
            "source_segment_id": self.source_segment_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def check_words_saved(cls, words):
        """
        批量检查多个单词是否已被收藏
        :param words: 单词列表
        :return: {word: vocabulary_id} 的字典
        """
        saved_words = cls.objects(word__in=words).only('word', 'id')
        return {
            vocab.word: str(vocab.id) 
            for vocab in saved_words
        }