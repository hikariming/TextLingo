from flask import Blueprint, request, jsonify
from services.material_service import MaterialService
from utils.response import success_response, error_response
from werkzeug.utils import secure_filename
import os
import uuid

material_bp = Blueprint('material', __name__, url_prefix='/api/materials')

ALLOWED_EXTENSIONS = {'txt', 'md', 'docx' }
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB

def secure_chinese_filename(filename):
    # Get the file extension
    if '.' not in filename:
        return None
    ext = filename.rsplit('.', 1)[1].lower()
    # Generate a unique filename with the original extension
    return f"{str(uuid.uuid4())}.{ext}"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@material_bp.route('/', methods=['POST'])
def create_material():
    if 'file' not in request.files:
        return error_response("No file part", 400)

    file = request.files['file']
    if file.filename == '':
        return error_response("No selected file", 400)
    
    original_filename = file.filename
    if not allowed_file(original_filename):
        return error_response(f"File type not allowed", 400)
    
    # Generate a secure filename while preserving the original name for the database
    filename = secure_chinese_filename(original_filename)
    if not filename:
        return error_response("Invalid filename", 400)
    
    # 读取文件内容为二进制，仅用于验证和保存文件
    content = file.read()
    if not content:
        return error_response("Empty file", 400)
    
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        return error_response("File size exceeds limit", 400)

    # Save content to data folder
    data_folder = os.path.join(os.getcwd(), 'data')
    os.makedirs(data_folder, exist_ok=True)
    file_path = os.path.join(data_folder, filename)
    
    # 以二进制模式写入文件
    with open(file_path, 'wb') as f:
        f.write(content)

    material = MaterialService.create_material(
        title=original_filename,  # Use original filename as title
        file_type=filename.rsplit('.', 1)[1].lower(),
        file_size=file_size,
        file_path=filename,  # Store the generated filename
        user_id=request.user_id if hasattr(request, 'user_id') else None
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