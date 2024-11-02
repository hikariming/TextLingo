from flask import Blueprint, request, jsonify
from services.material_service import MaterialService
from utils.response import success_response, error_response
from werkzeug.utils import secure_filename
import os
import uuid
from docx import Document
import io

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

    factory_id = request.form.get('factory_id')
    if not factory_id:
        return error_response("Factory ID is required", 400)

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

    # Update data folder paths
    base_data_folder = os.path.join(os.getcwd(), 'data')
    uploaded_folder = os.path.join(base_data_folder, 'step0_uploaded_file')
    txt_folder = os.path.join(base_data_folder, 'step1_get_txt')
    
    # Create directories if they don't exist
    os.makedirs(uploaded_folder, exist_ok=True)
    os.makedirs(txt_folder, exist_ok=True)
    
    file_extension = filename.rsplit('.', 1)[1].lower()
    
    if file_extension == 'docx':
        # Save original docx file
        docx_path = os.path.join(uploaded_folder, filename)
        with open(docx_path, 'wb') as f:
            f.write(content)
            
        # Process docx file
        doc = Document(docx_path)
        text_content = '\n'.join([paragraph.text for paragraph in doc.paragraphs if paragraph.text])
        
        # Generate txt filename and save
        txt_filename = f"{filename.rsplit('.', 1)[0]}.txt"
        txt_path = os.path.join(txt_folder, txt_filename)
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
            
        # Update file info but keep original file
        filename = txt_filename
        file_type = 'txt'
        file_size = len(text_content.encode('utf-8'))
        original_file_path = os.path.join('step0_uploaded_file', filename)  # 原文件路径
        processed_file_path = os.path.join('step1_get_txt', txt_filename)   # 处理后的文件路径
        
        material = MaterialService.create_material(
            title=original_filename,
            file_type=file_extension,
            file_size=file_size,
            file_path=processed_file_path,          # 处理后的文件路径
            original_file_path=original_file_path,  # 原文件路径
            original_filename=original_filename,
            user_id=request.user_id if hasattr(request, 'user_id') else None,
            status="pending_segmentation",
            factory_id=factory_id
        )
    elif file_extension in ['txt', 'md']:
        # Save original file
        original_path = os.path.join(uploaded_folder, filename)
        with open(original_path, 'wb') as f:
            f.write(content)
        
        # Read and save as txt in step1 folder
        text_content = content.decode('utf-8')
        txt_path = os.path.join(txt_folder, filename)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
            
        file_size = len(text_content.encode('utf-8'))
        material = MaterialService.create_material(
            title=original_filename,
            file_type=file_extension,
            file_size=file_size,
            file_path=txt_path,
            original_file_path=original_path,
            original_filename=original_filename,
            user_id=request.user_id if hasattr(request, 'user_id') else None,
            status="pending_segmentation",
            factory_id=factory_id
        )
    else:
        # Save other file types in uploaded folder
        file_path = os.path.join(uploaded_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(content)

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