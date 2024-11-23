# api/controllers/user_vocabulary_controller.py
from flask import Blueprint, request
from services.user_vocabulary_service import UserVocabularyService
from utils.response import success_response, error_response
from models.user_vocabulary import UserVocabulary
from models.setting import Setting

vocabulary_bp = Blueprint('vocabulary', __name__)

@vocabulary_bp.route('/vocabularies', methods=['POST'])
def create_vocabulary():
    try:
        data = request.get_json()
        if not data or 'word' not in data or 'meaning' not in data:
            return error_response("Missing required fields", 400)

        vocabulary = UserVocabularyService.create_vocabulary(
            word=data['word'],
            meaning=data['meaning'],
            reading=data.get('reading'),
            source_segment_id=data.get('source_segment_id')
        )
        return success_response(vocabulary.to_dict(), "Vocabulary created successfully")
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies', methods=['GET'])
def list_vocabularies():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        result = UserVocabularyService.list_vocabularies(
            page=page,
            per_page=per_page
        )
        return success_response(result)
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies/<vocabulary_id>', methods=['GET'])
def get_vocabulary(vocabulary_id):
    vocabulary = UserVocabularyService.get_vocabulary(vocabulary_id)
    if not vocabulary:
        return error_response("Vocabulary not found", 404)
    return success_response(vocabulary.to_dict())

@vocabulary_bp.route('/vocabularies/<vocabulary_id>', methods=['PUT'])
def update_vocabulary(vocabulary_id):
    data = request.get_json()
    vocabulary = UserVocabularyService.update_vocabulary(vocabulary_id, data)
    if not vocabulary:
        return error_response("Vocabulary not found", 404)
    return success_response(vocabulary.to_dict(), "Vocabulary updated successfully")

@vocabulary_bp.route('/vocabularies/<vocabulary_id>', methods=['DELETE'])
def delete_vocabulary(vocabulary_id):
    if UserVocabularyService.delete_vocabulary(vocabulary_id):
        return success_response(None, "Vocabulary deleted successfully")
    return error_response("Vocabulary not found", 404)

@vocabulary_bp.route('/vocabularies/check', methods=['POST'])
def check_saved_words():
    try:
        data = request.get_json()
        if not data or 'words' not in data:
            return error_response("Missing words list", 400)
            
        words = data['words']
        if not isinstance(words, list):
            return error_response("Words must be a list", 400)
            
        saved_words = UserVocabulary.check_words_saved(words)
        return success_response(saved_words)
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies/<vocabulary_id>/sources', methods=['GET'])
def get_vocabulary_sources(vocabulary_id):
    try:
        result = UserVocabularyService.get_vocabulary_sources(vocabulary_id)
        if not result:
            return error_response("Vocabulary not found", 404)
        return success_response(result)
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies/review/next', methods=['GET'])
def get_next_review_word():
    """获取下一个要复习的单词"""
    try:
        vocabulary = UserVocabularyService.get_next_review_word()
        if not vocabulary:
            return success_response(None, "No words to review")
        return success_response(vocabulary)
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies/<vocabulary_id>/review', methods=['POST'])
def process_review_result():
    """处理复习结果"""
    try:
        data = request.get_json()
        if not data or 'result' not in data:
            return error_response("Missing review result", 400)

        result = data['result']
        vocabulary_id = data['vocabulary_id']
        
        if result == 'remembered':
            vocabulary = UserVocabularyService.mark_word_remembered(vocabulary_id)
        elif result == 'forgotten':
            vocabulary = UserVocabularyService.mark_word_forgotten(vocabulary_id)
        elif result == 'mastered':
            vocabulary = UserVocabularyService.mark_word_mastered(vocabulary_id)
        else:
            return error_response("Invalid review result", 400)

        if not vocabulary:
            return error_response("Vocabulary not found", 404)
            
        return success_response(vocabulary)
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies/review/stats', methods=['GET'])
def get_review_stats():
    """获取复习统计信息"""
    try:
        stats = UserVocabularyService.get_review_stats()
        return success_response(stats)
    except Exception as e:
        return error_response(str(e), 500)

@vocabulary_bp.route('/vocabularies/review/settings', methods=['POST'])
def update_review_settings():
    """更新复习设置"""
    try:
        data = request.get_json()
        if not data or 'daily_limit' not in data:
            return error_response("Missing daily limit", 400)
            
        daily_limit = int(data['daily_limit'])
        if daily_limit < 1:
            return error_response("Daily limit must be positive", 400)
            
        Setting.set_setting(
            'daily_review_limit',
            str(daily_limit),
            '每日复习单词数量限制'
        )
        
        return success_response({'daily_limit': daily_limit})
    except Exception as e:
        return error_response(str(e), 500)