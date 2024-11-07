from flask import Blueprint, request, jsonify
from services.user_grammar_service import UserGrammarService
from utils.response import success_response, error_response

grammar_bp = Blueprint('grammar', __name__)

@grammar_bp.route('/grammars', methods=['POST'])
def create_grammar():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'explanation' not in data:
            return error_response("Missing required fields", 400)

        grammar = UserGrammarService.create_grammar(
            user_id=request.user_id,
            name=data['name'],
            explanation=data['explanation'],
            source_segment_id=data.get('source_segment_id')
        )
        return success_response(grammar.to_dict(), "Grammar created successfully")
    except Exception as e:
        return error_response(str(e), 500)

@grammar_bp.route('/grammars', methods=['GET'])
def list_grammars():
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        result = UserGrammarService.list_user_grammars(
            user_id=request.user_id,
            page=page,
            per_page=per_page
        )
        return success_response(result)
    except Exception as e:
        return error_response(str(e), 500)

@grammar_bp.route('/grammars/<grammar_id>', methods=['GET'])
def get_grammar(grammar_id):
    grammar = UserGrammarService.get_grammar(grammar_id)
    if not grammar:
        return error_response("Grammar not found", 404)
    return success_response(grammar.to_dict())

@grammar_bp.route('/grammars/<grammar_id>', methods=['PUT'])
def update_grammar(grammar_id):
    data = request.get_json()
    grammar = UserGrammarService.update_grammar(grammar_id, data)
    if not grammar:
        return error_response("Grammar not found", 404)
    return success_response(grammar.to_dict(), "Grammar updated successfully")

@grammar_bp.route('/grammars/<grammar_id>', methods=['DELETE'])
def delete_grammar(grammar_id):
    if UserGrammarService.delete_grammar(grammar_id):
        return success_response(None, "Grammar deleted successfully")
    return error_response("Grammar not found", 404)