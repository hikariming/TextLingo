from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra='ignore')
    """应用配置"""
    
    # 应用基础配置
    app_name: str = "TextLingo2 API"
    app_version: str = "1.0.5"
    debug: bool = False
    
    # Supabase 配置
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    
    # JWT 配置
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7天 = 7 * 24 * 60
    refresh_token_expire_days: int = 30  # 30天
    
    # Redis 缓存配置
    redis_host: Optional[str] = None
    redis_port: Optional[int] = None
    redis_db: int = 1
    redis_password: Optional[str] = None
    redis_ssl: bool = True
    redis_connection_pool_size: int = 10
    redis_socket_timeout: float = 5.0
    redis_socket_connect_timeout: float = 5.0
    redis_max_connections: int = 50

    # 缓存配置
    cache_enabled: bool = True
    cache_default_ttl: int = 300  # 5分钟
    cache_key_prefix: str = "api"
    
    # 日志配置
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    enable_debug_logs: bool = False  # 控制调试日志的开关
    enable_rls_debug: bool = False  # 专门控制RLS调试日志
    enable_http_logs: bool = False  # 控制HTTP请求日志
    log_sql_queries: bool = False  # 控制SQL查询日志
    
    # API 配置
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # 安全配置
    secret_key: str
    
    # AI 和 LangChain 配置
    google_api_key: Optional[str] = None  # Gemini API Key
    openrouter_api_key: Optional[str] = None  # OpenRouter API Key  
    minimax_api_key: Optional[str] = None # Minimax API Key
    minimax_groupid: Optional[str] = None # Minimax Group ID
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    dashscope_api_key: Optional[str] = None  # 阿里云百炼 API Key (通义千问)
    
    # 默认模型配置
    default_gemini_model: str = "deepseek-chat-v3"  # 改为使用DeepSeek
    default_openrouter_model: str = "deepseek/deepseek-chat-v3-0324"
    
    # AI 服务配置
    ai_request_timeout: int = 30  # 秒
    max_tokens: int = 2048
    temperature: float = 0.7
    
    # Dify 配置 (现在通过 dify_config.json 管理)
    # 如果需要兼容性，可以通过环境变量覆盖默认配置
    dify_legacy_api_url: Optional[str] = None  # 兼容性配置
    dify_legacy_api_token: Optional[str] = None  # 兼容性配置
    
    # 跨版本认证配置
    textlingo1_api_url: str = "https://textlingoclose-production.up.railway.app"  # TextLingo1 API 地址
    
    # Google OAuth配置
    google_oauth_client_id: Optional[str] = None
    google_oauth_client_secret: Optional[str] = None
    
    # 站点配置
    site_url: str = "http://localhost:3000"  # 前端网站地址，生产环境需要修改
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# 创建全局配置实例
settings = Settings()
