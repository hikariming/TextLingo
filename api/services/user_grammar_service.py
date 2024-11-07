from models.user_grammar import UserGrammar
from mongoengine.errors import DoesNotExist

class UserGrammarService:
    @staticmethod
    def create_grammar(user_id, name, explanation, source_segment_id=None):
        grammar = UserGrammar(
            user_id=user_id,
            name=name,
            explanation=explanation,
            source_segment_id=source_segment_id
        )
        grammar.save()
        return grammar

    @staticmethod
    def get_grammar(grammar_id):
        try:
            return UserGrammar.objects.get(id=grammar_id)
        except DoesNotExist:
            return None

    @staticmethod
    def list_user_grammars(user_id, page=1, per_page=20):
        skip = (page - 1) * per_page
        grammars = UserGrammar.objects(user_id=user_id).order_by('-created_at').skip(skip).limit(per_page)
        total = UserGrammar.objects(user_id=user_id).count()
        return {
            'items': [g.to_dict() for g in grammars],
            'total': total,
            'page': page,
            'per_page': per_page
        }

    @staticmethod
    def delete_grammar(grammar_id):
        try:
            grammar = UserGrammar.objects.get(id=grammar_id)
            grammar.delete()
            return True
        except DoesNotExist:
            return False

    @staticmethod
    def update_grammar(grammar_id, data):
        try:
            grammar = UserGrammar.objects.get(id=grammar_id)
            grammar.update(**data)
            grammar.reload()
            return grammar
        except DoesNotExist:
            return None