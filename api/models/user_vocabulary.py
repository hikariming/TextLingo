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
            "updated_at": self.updated_at,
            "review_stage": self.review_stage,
            "familiarity_level": self.familiarity_level,
            "mastered": self.mastered,
            "review_count": self.review_count,
            "correct_count": self.correct_count,
            "next_review_at": self.next_review_at
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
        # 修改为凌晨2点作为一天的开始
        now = datetime.utcnow()
        today_start = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if now.hour < 2:  # 如果当前时间在凌晨2点前，则使用前一天的凌晨2点
            today_start = today_start - timedelta(days=1)
        today_end = today_start + timedelta(days=1)
        
        # 获取今日需要复习的总数（包括未复习的和今天已复习的）
        total_review = cls.objects(
            (Q(mastered=False) | Q(mastered=None)) &  # 未掌握或未设置掌握状态
            (
                (Q(next_review_at__lte=today_end) | Q(next_review_at=None)) |  # 需要复习或未设置复习时间
                (Q(updated_at__gte=today_start) & Q(updated_at__lt=today_end) & Q(review_count__gt=0))  # 今天已复习的
            )
        ).count()
        
        # 获取今日实际已复习数量（只统计 review_count > 0 的）
        reviewed_words = cls.objects(
            Q(updated_at__gte=today_start) & 
            Q(updated_at__lt=today_end) &
            Q(review_count__gt=0)  # 确保只统计真正复习过的单词
        )
        
        reviewed_count = reviewed_words.count()
        
        # 计算今日正确率
        total_attempts = 0
        correct_attempts = 0
        for vocab in reviewed_words:
            total_attempts += 1
            if vocab.correct_count and vocab.correct_count > 0:
                correct_attempts += 1
            
        accuracy_rate = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        return {
            "total_review": total_review,
            "reviewed_count": reviewed_count,
            "remaining_count": max(0, total_review - reviewed_count),
            "accuracy_rate": round(accuracy_rate, 2)
        }

    @classmethod
    def get_next_review_words(cls, limit=None):
        """获取待复习单词列表"""
        print("开始获取待复习单词")
        # 修改为凌晨2点作为一天的开始
        now = datetime.utcnow()
        today_start = now.replace(hour=2, minute=0, second=0, microsecond=0)
        if now.hour < 2:  # 如果当前时间在凌晨2点前，则使用前一天的凌晨2点
            today_start = today_start - timedelta(days=1)
        
        # 获取每日复习数量设置
        from models.setting import Setting
        daily_limit = Setting.get_setting('daily_review_limit', '20')
        daily_limit = int(daily_limit)
        print(f"每日复习限制: {daily_limit}")
        
        # 获取今日已复习数量
        reviewed_today = cls.objects(
            Q(updated_at__gte=today_start) &
            Q(review_count__gt=0)  # 确保是真实复习过的
        ).count()
        print(f"今日已复习数量: {reviewed_today}")
        
        # 计算剩余可复习数量
        remaining_limit = daily_limit - reviewed_today
        print(f"剩余可复习数量: {remaining_limit}")
        
        if remaining_limit <= 0:
            print("已达到每日限制")
            return []
        
        # 如果指定了limit，使用较小的值
        if limit:
            remaining_limit = min(int(limit), remaining_limit)
        
        # 统一查询条件
        base_query = (
            (Q(mastered=False) | Q(mastered=None)) &  # 未掌握或未设置掌握状态
            (
                Q(updated_at__lt=today_start) |  # 今天未复习
                Q(updated_at=None) |             # 或未设置更新时间
                Q(review_stage=0) |              # 或是新单词
                Q(review_stage=None)             # 或未设置复习阶段
            )
        )
        
        # 分步检查查询条件，使用相同的 base_query
        print("检查数据库中的单词状态：")
        
        # 1. 检查未掌握的单词数量
        unmastered_count = cls.objects(Q(mastered=False) | Q(mastered=None)).count()
        print(f"未掌握的单词数量: {unmastered_count}")
        
        # 2. 检查今天未复习的单词数量
        not_reviewed_today = cls.objects(
            Q(updated_at__lt=today_start) | Q(updated_at=None)
        ).count()
        print(f"今天未复习的单词数量: {not_reviewed_today}")
        
        # 3. 检查需要复习的单词数量 - 使用相同的 base_query
        need_review = cls.objects(base_query).count()
        print(f"需要复习的单词数量: {need_review}")
        
        # 使用相同的查询条件获取单词
        words = cls.objects(base_query).limit(remaining_limit)
        found_count = words.count()
        print(f"最终找到待复习单词数量: {found_count}")
        
        # 如果没找到单词，打印一些额外信息
        if found_count == 0:
            print("没有找到待复习单词，检查第一个未掌握的单词：")
            first_word = cls.objects(Q(mastered=False) | Q(mastered=None)).first()
            if first_word:
                print(f"单词: {first_word.word}")
                print(f"更新时间: {first_word.updated_at}")
                print(f"下次复习时间: {first_word.next_review_at}")
                print(f"复习阶段: {first_word.review_stage}")
        
        return words