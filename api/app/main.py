from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog
import os
from datetime import datetime
from fastapi import Request

from app.core.config import settings
from app.services.supabase_client import SupabaseService
supabase_service = SupabaseService()
from app.api.v1.api_router import api_router
from app.services.user_service import UserService
from app.services.health_check_service import health_check_service

# Replit 环境检测
IS_REPLIT = os.getenv("REPL_SLUG") is not None

# 使用新的日志配置管理器
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.setup_logging()

# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="TextLingo2 后端API服务",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    swagger_ui_oauth2_redirect_url=f"{settings.api_v1_prefix}/docs/oauth2-redirect",
    swagger_ui_parameters={
        "persistAuthorization": True,
    }
)

# 添加 Gzip 压缩中间件 (Replit 优化)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 配置 CORS - 针对 Vercel 前端优化
cors_origins = settings.cors_origins.copy() if hasattr(settings, 'cors_origins') else []

# Replit 环境下添加额外的 CORS 配置
if IS_REPLIT:
    cors_origins.extend([
        "https://v2.textlingo.app",
        "https://www.textlingo.app",
        "https://textlingo.app",
        "https://*.vercel.app",
        "https://*.repl.co",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ])

# 添加开发环境的CORS支持
cors_origins.extend([
    "http://localhost:3000",
    "http://127.0.0.1:3000", 
    "http://localhost:3001",
    "http://127.0.0.1:3001"
])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,  # 预检请求缓存时间
)


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.detail}", status_code=exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred on the server."}
    )


# 健康检查端点
@app.get("/health", tags=["health"])
def health_check():
    """健康检查，增加数据库服务密钥诊断"""
    service_role_check = "pending"
    error_message = None
    try:
        # 使用服务密钥执行一个安全的只读操作，来验证密钥和权限
        response = supabase_service.get_client().table("user_profiles").select("id").limit(1).execute()
        service_role_check = "ok"
    except Exception as e:
        service_role_check = "failed"
        error_message = str(e)

    return {
        "status": "healthy", 
        "app_name": settings.app_name, 
        "time": "1741",
        "version": settings.app_version,
        "service_role_key_check": {
             "status": service_role_check,
             "error": error_message
        }
    }


# 根端点
@app.get("/", tags=["根"])
async def root():
    """根端点，显示API信息"""
    return {"message": "Welcome to TextLingo API"}


# 注册 API 路由
app.include_router(api_router, prefix=settings.api_v1_prefix)


# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行的事件
    """
    logger.info("Application startup...")
    # 验证 service_role key
    await health_check_service.verify_service_role_key()
    
    # 可以在这里添加其他的启动任务
    # ...


# 应用关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{settings.app_name} shutdown")


if __name__ == "__main__":
    import uvicorn
    import os
    
    # 获取端口，支持 Replit 和其他平台
    PORT = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=settings.debug
    )
