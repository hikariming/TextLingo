"""
Replit 专用配置文件
优化 FastAPI 应用在 Replit 环境中的运行
"""
import os
from typing import List

class ReplitConfig:
    """Replit 环境配置"""
    
    # 基础配置
    APP_NAME: str = "TextLingo2 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 8000))
    
    # Supabase 配置
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    
    # 安全配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS 配置 - 针对 Vercel 前端
    CORS_ORIGINS: List[str] = [
        "https://textlingo.app",
        "https://www.textlingo.app",
        "https://v2.textlingo.app",
        "https://*.vercel.app",
        "http://localhost:3000",  # 本地开发
        "http://127.0.0.1:3000"   # 本地开发
    ]
    
    # API 配置
    API_V1_PREFIX: str = "/api/v1"
    
    # Replit 特定配置
    REPL_SLUG: str = os.getenv("REPL_SLUG", "textlingo2-api")
    REPL_OWNER: str = os.getenv("REPL_OWNER", "")
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """验证必需的配置项"""
        errors = []
        
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is required")
        
        if not cls.SUPABASE_ANON_KEY:
            errors.append("SUPABASE_ANON_KEY is required")
            
        if not cls.JWT_SECRET_KEY:
            errors.append("JWT_SECRET_KEY is required")
            
        if not cls.SECRET_KEY:
            errors.append("SECRET_KEY is required")
            
        return errors
    
    @classmethod
    def get_repl_url(cls) -> str:
        """获取 Repl 的 URL"""
        if cls.REPL_OWNER and cls.REPL_SLUG:
            return f"https://{cls.REPL_SLUG}.{cls.REPL_OWNER}.repl.co"
        return f"https://{cls.REPL_SLUG}.repl.co"

# 全局配置实例
replit_config = ReplitConfig()