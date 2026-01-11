from flask import Blueprint, request, jsonify
from services.user_service import UserService

user_bp = Blueprint('user', __name__, url_prefix='/api/users')

@user_bp.route('/', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    if not username or not email:
        return jsonify({"error": "Missing required fields"}), 400
        
    user = UserService.create_user(username, email)
    return jsonify(user.to_dict()), 201

@user_bp.route('/<username>', methods=['GET'])
def get_user(username):
    user = UserService.get_user_by_username(username)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200