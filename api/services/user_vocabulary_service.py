from models.user_vocabulary import UserVocabulary
from mongoengine.errors import DoesNotExist
from models.material_segment import MaterialSegment
from datetime import datetime, timedelta
from mongoengine.queryset.visitor import Q

class UserVocabularyService:
    @staticmethod
    def create_vocabulary(word, meaning, reading=None, source_segment_id=None):
        vocabulary = UserVocabulary(
            word=word,
            meaning=meaning,
            reading=reading,
            source_segment_id=source_segment_id
        )
        vocabulary.save()
        return vocabulary

    @staticmethod
    def get_vocabulary(vocabulary_id):
        try:
            return UserVocabulary.objects.get(id=vocabulary_id)
        except DoesNotExist:
            return None

    @staticmethod
    def list_vocabularies(page=1, per_page=20):
        skip = (page - 1) * per_page
        vocabularies = UserVocabulary.objects.order_by('-created_at').skip(skip).limit(per_page)
        total = UserVocabulary.objects.count()
        return {
            'items': [v.to_dict() for v in vocabularies],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def delete_vocabulary(vocabulary_id):
        try:
            vocabulary = UserVocabulary.objects.get(id=vocabulary_id)
            vocabulary.delete()
            return True
        except DoesNotExist:
            return False

    @staticmethod
    def update_vocabulary(vocabulary_id, data):
        try:
            vocabulary = UserVocabulary.objects.get(id=vocabulary_id)
            vocabulary.update(**data)
            vocabulary.reload()
            return vocabulary
        except DoesNotExist:
            return None

    @staticmethod
    def get_vocabulary_sources(vocabulary_id):
        try:
            # 获取词汇信息
            vocabulary = UserVocabulary.objects.get(id=vocabulary_id)
            
            # 在所有材料段落中搜索包含该单词的内容
            segments = MaterialSegment.objects(original__contains=vocabulary.word).only(
                'material_id', 'original', 'translation'
            )
            
            # 构建返回结果
            sources = [{
                'material_id': str(segment.material_id),
                'segment_id': str(segment.id),
                'original': segment.original,
                'translation': segment.translation
            } for segment in segments]
            
            return {
                'vocabulary': vocabulary.to_dict(),
                'sources': sources
            }
        except DoesNotExist:
            return None

    @staticmethod
    def get_review_stats():
        """获取复习统计信息"""
        return UserVocabulary.get_today_review_stats()

    @staticmethod
    def get_next_review_word():
        """获取下一个需要复习的单词"""
        words = UserVocabulary.get_next_review_words(limit=1)
        if not words:
            return None
        return words[0].to_dict()

    @staticmethod
    def mark_word_remembered(vocabulary_id):
        """标记单词为已记住"""
        try:
            vocabulary = UserVocabulary.objects.get(id=vocabulary_id)
            
            # 更新复习进度
            vocabulary.review_count += 1
            vocabulary.correct_count += 1
            vocabulary.review_stage = min(vocabulary.review_stage + 1, 5)
            
            # 计算下次复习时间
            days = UserVocabulary.get_next_review_interval(vocabulary.review_stage)
            vocabulary.next_review_at = datetime.utcnow() + timedelta(days=days)
            
            # 更新熟悉度
            vocabulary.familiarity_level = min(
                int((vocabulary.correct_count / max(vocabulary.review_count, 1)) * 5),
                5
            )
            
            vocabulary.save()
            return vocabulary.to_dict()
        except DoesNotExist:
            return None

    @staticmethod
    def mark_word_forgotten(vocabulary_id):
        """标记单词为未记住"""
        try:
            vocabulary = UserVocabulary.objects.get(id=vocabulary_id)
            
            # 更新复习进度
            vocabulary.review_count += 1
            vocabulary.review_stage = 0
            vocabulary.next_review_at = datetime.utcnow() + timedelta(days=1)
            
            # 更新熟悉度
            vocabulary.familiarity_level = min(
                int((vocabulary.correct_count / max(vocabulary.review_count, 1)) * 5),
                5
            )
            
            vocabulary.save()
            return vocabulary.to_dict()
        except DoesNotExist:
            return None

    @staticmethod
    def mark_word_mastered(vocabulary_id):
        """标记单词为已掌握"""
        try:
            vocabulary = UserVocabulary.objects.get(id=vocabulary_id)
            vocabulary.mastered = True
            vocabulary.familiarity_level = 5
            vocabulary.save()
            return vocabulary.to_dict()
        except DoesNotExist:
            return None