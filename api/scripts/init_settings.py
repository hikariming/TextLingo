import yaml
from models.setting import Setting

def init_settings():
    # 读取配置文件
    with open('api/config.yml', 'r') as file:
        config = yaml.safe_load(file)
    
    # 保存 MongoDB 配置
    Setting.set_setting(
        'mongodb_uri', 
        config['mongodb']['uri'],
        'MongoDB connection URI'
    )
    
    # 保存 LLM 配置
    Setting.set_setting(
        'llm_api_key',
        config['llm_api_key'],
        'LLM API Key'
    )
    
    Setting.set_setting(
        'llm_model',
        config['llm_model'],
        'LLM Model Name'
    )
    
    Setting.set_setting(
        'llm_base_url',
        config['llm_base_url'],
        'LLM Base URL'
    )

if __name__ == '__main__':
    init_settings()