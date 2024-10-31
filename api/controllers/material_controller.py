from flask import Blueprint, request, jsonify
from services.material_service import MaterialService
from utils.response import success_response, error_response
from werkzeug.utils import secure_filename
import os

material_bp = Blueprint('material', __name__, url_prefix='/api/materials')

ALLOWED_EXTENSIONS = {'txt', 'md', 'pdf', 'html', 'xlsx', 'xls', 'docx', 'csv', 'htm'}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@material_bp.route('/', methods=['POST'])
def create_material():
    if 'file' not in request.files:
        return error_response("No file provided", 400)
    
    file = request.files['file']
    if file.filename == '':
        return error_response("No selected file", 400)
    
    if not allowed_file(file.filename):
        return error_response("File type not allowed", 400)
    
    if file.content_length > MAX_FILE_SIZE:
        return error_response("File size exceeds limit", 400)

    filename = secure_filename(file.filename)
    content = file.read()
    file_size = len(content)
    file_type = filename.rsplit('.', 1)[1].lower()
    
    material = MaterialService.create_material(
        title=filename,
        content=content,
        file_type=file_type,
        file_size=file_size,
        user_id=request.user_id  # 假设通过认证中间件设置
    )
    
    return success_response(material.to_dict(), "Material created successfully")

@material_bp.route('/', methods=['GET'])
def get_materials():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    materials = MaterialService.get_materials(
        user_id=request.user_id,
        page=page,
        per_page=per_page
    )
    
    return success_response(materials)

@material_bp.route('/<material_id>', methods=['GET'])
def get_material(material_id):
    material = MaterialService.get_material_by_id(material_id)
    if not material:
        return error_response("Material not found", 404)
    return success_response(material)

@material_bp.route('/<material_id>', methods=['PUT'])
def update_material(material_id):
    data = request.get_json()
    result = MaterialService.update_material(material_id, data)
    if result.modified_count:
        return success_response(None, "Material updated successfully")
    return error_response("Material not found", 404)

@material_bp.route('/<material_id>', methods=['DELETE'])
def delete_material(material_id):
    result = MaterialService.delete_material(material_id)
    if result.deleted_count:
        return success_response(None, "Material deleted successfully")
    return error_response("Material not found", 404)