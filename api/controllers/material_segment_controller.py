from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
from services.material_segment_service import MaterialSegmentService
from services.material_service import MaterialService
from utils.response import success_response, error_response
import os

material_segment_bp = Blueprint('material_segment', __name__, url_prefix='/api/material-segments')

@material_segment_bp.route('/segment-material/<material_id>', methods=['POST', 'OPTIONS'])
@cross_origin()
def segment_material(material_id):
    if request.method == 'OPTIONS':
        return success_response(None)
        
    try:
        # 打印调试信息
        print(f"Processing material_id: {material_id}")
        
        data = request.get_json()
        if not data:
            return error_response("No JSON data provided", 400)
            
        # 将默认值改为 'paragraph'
        segmentation_type = data.get('segmentation_type', 'paragraph')
        print(f"Segmentation type: {segmentation_type}")
        
        # 从Material获取文本内容
        base_data_folder = os.path.join(os.getcwd(), 'data')
        material = MaterialService.get_material_by_id(material_id)
        
        if not material:
            print(f"Material not found for ID: {material_id}")
            return error_response("Material not found", 404)
            
        file_path = os.path.join(base_data_folder, material['file_path'])
        print(f"File path: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"File not found at path: {file_path}")
            return error_response("File not found", 404)
            
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"Error reading file: {str(e)}")
            return error_response(f"Error reading file: {str(e)}", 500)
            
        # 进行分段处理
        try:
            segments = MaterialSegmentService.segment_text(
                material_id=material_id,  # 直接传入字符串ID
                text=content,
                segmentation_type=segmentation_type
            )
            
            # 转换结果为字典列表
            segments_data = [segment.to_dict() for segment in segments]
            
            # 更新material状态
            MaterialService.update_material(material_id, {"status": "segmented"})
            
            return success_response(segments_data, "Material segmented successfully")
            
        except Exception as e:
            print(f"Error in segment_text: {str(e)}")
            return error_response(f"Error in segmentation: {str(e)}", 500)
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return error_response(f"Error segmenting material: {str(e)}", 500)

@material_segment_bp.route('/material/<material_id>', methods=['GET', 'OPTIONS'])
@cross_origin()
def get_material_segments(material_id):
    if request.method == 'OPTIONS':
        return success_response(None)
        
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        segments = MaterialSegmentService.get_segments_by_material(
            material_id,
            page=page,
            per_page=per_page
        )
        
        return success_response([segment.to_dict() for segment in segments])
        
    except Exception as e:
        return error_response(f"Error fetching segments: {str(e)}", 500)

@material_segment_bp.route('/<segment_id>', methods=['PUT'])
def update_segment(segment_id):
    try:
        data = request.get_json()
        segment = MaterialSegmentService.update_segment(segment_id, data)
        return success_response(segment.to_dict(), "Segment updated successfully")
        
    except Exception as e:
        return error_response(f"Error updating segment: {str(e)}", 500)

@material_segment_bp.route('/<segment_id>', methods=['DELETE'])
def delete_segment(segment_id):
    try:
        MaterialSegmentService.delete_segment(segment_id)
        return success_response(None, "Segment deleted successfully")
        
    except Exception as e:
        return error_response(f"Error deleting segment: {str(e)}", 500)