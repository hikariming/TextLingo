from flask import jsonify, request, Blueprint
from services.setting_service import SettingService

# 创建Blueprint
setting_bp = Blueprint('setting', __name__)

class SettingController:
    @staticmethod
    @setting_bp.route('/setting', methods=['GET'])
    def get_config():
        """获取所有LLM相关配置"""
        try:
            config = SettingService.get_llm_config()
            return jsonify(config), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @setting_bp.route('/setting', methods=['PUT'])
    def update_config():
        """更新LLM配置"""
        try:
            data = request.get_json()
            config = SettingService.update_llm_config(data)
            return jsonify(config), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
