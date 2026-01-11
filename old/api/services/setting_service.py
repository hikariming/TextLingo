from models.setting import Setting

class SettingService:
    @staticmethod
    def get_llm_config():
        """获取LLM相关的所有配置"""
        config = {
            "llm_api_key": Setting.get_setting("llm_api_key", ""),
            "llm_base_url": Setting.get_setting("llm_base_url", ""),
            "llm_model": Setting.get_setting("llm_model", "claude-3-5-sonnet-20241022")
        }
        return config

    @staticmethod
    def update_llm_config(data):
        """更新LLM配置"""
        for key, value in data.items():
            Setting.set_setting(key, value)
        return data

    @staticmethod
    def get_vocabulary_config():
        """获取词汇相关的所有配置"""
        config = {
            "daily_review_limit": int(Setting.get_setting("daily_review_limit", "20"))
        }
        return config

    @staticmethod
    def update_vocabulary_config(data):
        """更新词汇配置"""
        for key, value in data.items():
            Setting.set_setting(key, str(value))
        return data
