# api/controllers/user_vocabulary_controller.py
from flask import Blueprint, request, jsonify
from services.user_vocabulary_service import UserVocabularyService
from utils.response import success_response, error_response

vocabulary_bp = Blueprint('vocabulary', __name__)

@vocabulary_bp.route('/vocabularies', methods=['POST'])
def create_vocabulary():
    try:
        data = request.get_json()
        if not data or 'word' not in data or 'meaning' not in data:
            return error_response("Missing required fields", 400)

        vocabulary = UserVocabularyService.create_vocabulary(
            user_id=request.user_id,
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
        result = UserVocabularyService.list_user_vocabularies(
            user_id=request.user_id,
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