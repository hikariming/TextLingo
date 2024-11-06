from flask import Blueprint, request, jsonify
from services.material_service import MaterialService
from services.translation_service import TranslationService
from utils.response import success_response, error_response
import os
import uuid
from docx import Document
import io
from flask import current_app
import asyncio
from bson.objectid import ObjectId
import traceback
from threading import Thread
import json
from services.material_segment_service import MaterialSegmentService

material_bp = Blueprint('material', __name__)

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

@material_bp.route('/materials', methods=['POST'])
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
        original_file_path = os.path.join('step0_uploaded_file', os.path.basename(docx_path))  # Keep original docx extension
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
        return success_response(material, "Material created successfully")
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
        return success_response(material, "Material created successfully")
    else:
        # Save other file types in uploaded folder
        file_path = os.path.join(uploaded_folder, filename)
        with open(file_path, 'wb') as f:
            f.write(content)

    return success_response(material.to_dict(), "Material created successfully")

@material_bp.route('/materials', methods=['GET'])
def get_materials():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    materials = MaterialService.get_materials(
        user_id=request.user_id,
        page=page,
        per_page=per_page
    )
    
    return success_response(materials)

@material_bp.route('/materials/<material_id>', methods=['GET'])
def get_material(material_id):
    material = MaterialService.get_material_by_id(material_id)
    if not material:
        return error_response("Material not found", 404)
    return success_response(material)

@material_bp.route('/materials/<material_id>', methods=['PUT'])
def update_material(material_id):
    data = request.get_json()
    result = MaterialService.update_material(material_id, data)
    if result.modified_count:
        return success_response(None, "Material updated successfully")
    return error_response("Material not found", 404)

@material_bp.route('/materials/<material_id>', methods=['DELETE'])
def delete_material(material_id):
    try:
        # Get material info before deletion
        material = MaterialService.get_material_by_id(material_id)
        if not material:
            return error_response("Material not found", 404)

        # Delete associated files if they exist
        base_data_folder = os.path.join(os.getcwd(), 'data')
        
        # Try to delete processed file (txt)
        if material.get('file_path'):
            processed_file_path = os.path.join(base_data_folder, material['file_path'])
            try:
                if os.path.exists(processed_file_path):
                    os.remove(processed_file_path)
            except Exception as e:
                print(f"Warning: Could not delete processed file: {str(e)}")

        # Try to delete original file
        if material.get('original_file_path'):
            original_file_path = os.path.join(base_data_folder, material['original_file_path'])
            try:
                if os.path.exists(original_file_path):
                    os.remove(original_file_path)
            except Exception as e:
                print(f"Warning: Could not delete original file: {str(e)}")

        # Delete the material from database
        result = MaterialService.delete_material(material_id)
        
        if result:
            return success_response(None, "Material and associated files deleted successfully")
        return error_response("Material not found", 404)
        
    except Exception as e:
        print(f"Error deleting material: {str(e)}")
        return error_response(f"Error deleting material: {str(e)}", 500)

@material_bp.route('/materials/<material_id>/preview', methods=['GET'])
def get_material_preview(material_id):
    try:
        # 获取材料信息
        material = MaterialService.get_material_by_id(material_id)
        if not material:
            return error_response("Material not found", 404)

        # 构建完整的文件路径
        base_data_folder = os.path.join(os.getcwd(), 'data')
        file_path = os.path.join(base_data_folder, material['file_path'])

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return error_response("File not found", 404)

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # 读取前2000个字符
            
        # 按行分割内容并过滤掉空行
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        return success_response({
            "preview": lines,
            "total_length": len(content)
        })
        
    except Exception as e:
        return error_response(f"Error reading file: {str(e)}", 500)

@material_bp.route('/materials/<material_id>/translate', methods=['POST'])
def start_translation(material_id):
    try:
        if not ObjectId.is_valid(material_id):
            return error_response("Invalid material ID format", 400)
            
        # 检查 Content-Type
        if not request.is_json:
            data = request.get_data()
            try:
                # 尝试手动解析 JSON
                data = json.loads(data)
            except:
                # 如果没有数据，使用默认值
                data = {}
        else:
            data = request.get_json()

        target_language = data.get('target_language', 'zh-CN')
        enable_deep_explanation = data.get('enable_deep_explanation', False)
        
        # 更新材料态
        MaterialService.update_material(material_id, {
            'status': 'translating',
            'target_language': target_language,
            'enable_deep_explanation': enable_deep_explanation,
            'translation_status': 'processing'
        })
        
        # 创建新线程来处理翻译任务
        def run_translation():
            translation_service = TranslationService()
            try:
                translation_service.translate_material(material_id)
            except Exception as e:
                print(f"Translation error in thread: {str(e)}")
                # 更新失败状态
                MaterialService.update_material(material_id, {
                    'translation_status': 'failed',
                    'status': 'translation_failed'
                })
        
        thread = Thread(target=run_translation)
        thread.daemon = True  # 设置为守护线程
        thread.start()
        
        return success_response(None, "Translation started successfully")
    except Exception as e:
        print(f"Error starting translation: {str(e)}")
        print(traceback.format_exc())  # 打印完整的错误堆栈
        return error_response(f"Failed to start translation: {str(e)}", 500)

@material_bp.route('/materials/text', methods=['POST'])
def create_material_from_text():
    try:
        data = request.get_json()
        if not data or 'content' not in data or 'factory_id' not in data:
            return error_response("Missing content or factory_id", 400)

        content = data['content']
        factory_id = data['factory_id']
        
        if not content.strip():
            return error_response("Empty content", 400)

        # Generate a unique filename
        filename = f"{str(uuid.uuid4())}.txt"
        
        # Update data folder paths
        base_data_folder = os.path.join(os.getcwd(), 'data')
        uploaded_folder = os.path.join(base_data_folder, 'step0_uploaded_file')
        txt_folder = os.path.join(base_data_folder, 'step1_get_txt')
        
        # Create directories if they don't exist
        os.makedirs(uploaded_folder, exist_ok=True)
        os.makedirs(txt_folder, exist_ok=True)

        # Save original file
        original_path = os.path.join(uploaded_folder, filename)
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save processed file (in this case, same as original)
        txt_path = os.path.join(txt_folder, filename)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        file_size = len(content.encode('utf-8'))
        
        material = MaterialService.create_material(
            title=filename,
            file_type='txt',
            file_size=file_size,
            file_path=os.path.join('step1_get_txt', filename),
            original_file_path=os.path.join('step0_uploaded_file', filename),
            original_filename=filename,
            user_id=request.user_id if hasattr(request, 'user_id') else None,
            status="pending_segmentation",
            factory_id=factory_id
        )
        
        return success_response(material, "Material created successfully")
        
    except Exception as e:
        print(f"Error creating material from text: {str(e)}")
        return error_response(f"Failed to create material: {str(e)}", 500)