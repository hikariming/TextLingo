from models.user_vocabulary import UserVocabulary
from mongoengine.errors import DoesNotExist

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