from flask import jsonify, request, Blueprint
from services.setting_service import SettingService
from services.translation_service import TranslationService

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

    @staticmethod
    @setting_bp.route('/setting/test-llm', methods=['POST'])
    def test_llm_connection():
        """测试LLM API连接"""
        try:
            result = TranslationService.test_llm_connection()
            return jsonify(result), 200 if result["status"] == "success" else 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @setting_bp.route('/setting/vocabulary', methods=['GET'])
    def get_vocabulary_config():
        """获取词汇相关配置"""
        try:
            config = SettingService.get_vocabulary_config()
            return jsonify(config), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @staticmethod
    @setting_bp.route('/setting/vocabulary', methods=['PUT'])
    def update_vocabulary_config():
        """更新词汇相关配置"""
        try:
            data = request.get_json()
            config = SettingService.update_vocabulary_config(data)
            return jsonify(config), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
