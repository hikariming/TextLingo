from datetime import datetime, timedelta
from mongoengine import Document, StringField, DateTimeField, IntField, BooleanField
from mongoengine.queryset.visitor import Q

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
    
    # 新增字段
    review_stage = IntField(default=0)  # 复习阶段
    next_review_at = DateTimeField()  # 下次复习时间
    familiarity_level = IntField(default=0)  # 熟悉度 0-5
    mastered = BooleanField(default=False)  # 是否已掌握
    review_count = IntField(default=0)  # 复习次数
    correct_count = IntField(default=0)  # 正确次数

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

    @staticmethod
    def get_next_review_interval(stage):
        """获取下次复习间隔"""
        intervals = {
            0: 1,    # 1天
            1: 2,    # 2天
            2: 4,    # 4天
            3: 7,    # 7天
            4: 15,   # 15天
            5: 30    # 30天
        }
        return intervals.get(stage, 30)  # 默认30天

    @classmethod
    def get_today_review_stats(cls):
        """获取今日复习统计信息"""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # 获取今日需要复习的总数
        total_review = cls.objects(
            Q(mastered=False) & 
            (Q(next_review_at__lte=today_end) | Q(next_review_at=None))
        ).count()
        
        # 获取今日已复习数量
        reviewed_today = cls.objects(
            Q(updated_at__gte=today_start) & 
            Q(updated_at__lt=today_end) &
            Q(review_count__gt=0)
        ).count()
        
        # 计算今日正确率
        today_reviews = cls.objects(
            Q(updated_at__gte=today_start) & 
            Q(updated_at__lt=today_end)
        )
        
        total_attempts = 0
        correct_attempts = 0
        for vocab in today_reviews:
            total_attempts += vocab.review_count
            correct_attempts += vocab.correct_count
            
        accuracy_rate = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            "total_review": total_review,
            "reviewed_count": reviewed_today,
            "remaining_count": max(0, total_review - reviewed_today),
            "accuracy_rate": round(accuracy_rate, 2)
        }

    @classmethod
    def get_next_review_words(cls, limit=None):
        """获取待复习单词列表"""
        # 获取每日复习数量设置
        from models.setting import Setting
        daily_limit = Setting.get_setting('daily_review_limit', '20')
        daily_limit = int(daily_limit)
        
        # 如果指定了limit，使用较小的值
        if limit:
            daily_limit = min(int(limit), daily_limit)
            
        query = Q(mastered=False) & (
            Q(next_review_at__lte=datetime.utcnow()) |
            Q(next_review_at=None)
        )
        
        # 获取今日已复习数量
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        reviewed_today = cls.objects(
            Q(updated_at__gte=today_start) &
            Q(review_count__gt=0)
        ).count()
        
        # 如果今日已达到限制，返回空列表
        if reviewed_today >= daily_limit:
            return []
            
        # 返回剩余可复习的单词
        remaining_limit = daily_limit - reviewed_today
        return cls.objects(query).limit(remaining_limit)