"""
日志配置管理器
提供统一的日志配置和级别控制
"""

import logging
import structlog
import os
from typing import Dict, Any
from app.core.config import settings


class LoggingConfig:
    """日志配置管理器"""
    
    @staticmethod
    def setup_logging():
        """设置应用的日志配置"""
        
        # 配置结构化日志
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
        
        # 设置全局日志级别
        log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
        logging.basicConfig(level=log_level)
        
        # 配置第三方库的日志级别
        LoggingConfig._configure_third_party_loggers()
        
        return structlog.get_logger()
    
    @staticmethod
    def _configure_third_party_loggers():
        """配置第三方库的日志级别"""
        
        # HTTP客户端日志控制
        if not settings.enable_http_logs:
            # 降低 httpx 和 requests 的日志级别
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("requests").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        # 数据库日志控制
        if not settings.log_sql_queries:
            logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
            logging.getLogger("alembic").setLevel(logging.WARNING)
        
        
        # 其他第三方库
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("fastapi").setLevel(logging.INFO)
    
    @staticmethod
    def should_log_debug() -> bool:
        """判断是否应该记录调试日志"""
        return settings.enable_debug_logs or settings.debug
    
    @staticmethod
    def should_log_rls_debug() -> bool:
        """判断是否应该记录RLS调试日志"""
        return settings.enable_rls_debug or settings.debug
    
    @staticmethod
    def should_log_http() -> bool:
        """判断是否应该记录HTTP请求日志"""
        return settings.enable_http_logs or settings.debug
    
    @staticmethod
    def get_logger_for_service(service_name: str):
        """为特定服务获取配置好的logger"""
        logger = structlog.get_logger(service_name)
        return logger
    
    @staticmethod
    def log_error_with_context(logger, error: Exception, context: Dict[str, Any] = None):
        """记录带上下文的错误日志"""
        error_context = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            **(context or {})
        }
        logger.error("操作失败", **error_context)
    
    @staticmethod
    def log_user_action(logger, user_id: str, action: str, details: Dict[str, Any] = None):
        """记录用户操作日志（仅记录重要操作）"""
        if details:
            logger.info(f"用户操作: {action}", user_id=user_id, **details)
        else:
            logger.info(f"用户操作: {action}", user_id=user_id)


# 创建全局logger实例
def get_service_logger(service_name: str):
    """获取服务专用的logger"""
    return LoggingConfig.get_logger_for_service(service_name)


# 装饰器：用于自动记录函数执行
def log_function_call(logger_name: str = None):
    """装饰器：记录函数调用（仅在调试模式下）"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if LoggingConfig.should_log_debug():
                logger = structlog.get_logger(logger_name or func.__module__)
                logger.debug(f"调用函数: {func.__name__}", args=len(args), kwargs=list(kwargs.keys()))
            return func(*args, **kwargs)
        return wrapper
    return decorator