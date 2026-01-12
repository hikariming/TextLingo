
import structlog
from app.services.supabase_client import supabase_service
from gotrue.errors import AuthApiError
import uuid

logger = structlog.get_logger(__name__)

class HealthCheckService:
    """
    应用启动时的健康检查服务
    """
    
    async def verify_service_role_key(self) -> bool:
        """
        验证 SUPABASE_SERVICE_ROLE_KEY 是否有效且拥有 Auth Admin 权限。
        
        通过尝试调用一个需要管理员权限的API端点 (get_user_by_id) 来实现。
        """
        logger.info("🩺 [Health Check] Performing verification of SUPABASE_SERVICE_ROLE_KEY...")
        
        try:
            service_client = supabase_service.get_client()
            
            # 我们需要一个不存在的、随机的UUID来测试，以确保我们测试的是API权限，
            # 而不是用户是否存在。
            random_user_id = str(uuid.uuid4())
            
            # 这个调用需要 Auth Admin 权限。如果 service_role key 无效或权限不足，
            # 它会抛出 AuthApiError (403 Forbidden)。
            # 我们期望它因为 "user not found" (404) 而失败，这恰好证明了我们有权限调用它。
            service_client.auth.admin.get_user_by_id(random_user_id)

            # 如果代码执行到这里，说明没有抛出403 Forbidden，这是一个意外情况，但仍算作成功。
            # 正常情况应该在上面一行抛出 AuthApiError。
            logger.warning("🤔 [Health Check] get_user_by_id did not throw an exception as expected, but this still indicates the service key is likely valid.")
            return True

        except AuthApiError as e:
            # 这是我们期望的失败路径，我们需要检查错误码。
            if "User not found" in str(e.message):
                # 收到 "User not found" 是一个好迹象！
                # 这意味着我们的请求被成功认证，并且服务正常响应了我们的查询。
                logger.info("✅ [Health Check] SUPABASE_SERVICE_ROLE_KEY is valid and has Auth Admin privileges.")
                return True
            else:
                # 任何其他 AuthApiError (例如 401 Unauthorized, 403 Forbidden) 都表示密钥有问题。
                self._log_key_error(f"Auth API Error: {e.message}")
                return False
        
        except Exception as e:
            # 捕获其他任何异常，例如网络问题。
            self._log_key_error(f"An unexpected error occurred: {str(e)}")
            return False

    def _log_key_error(self, error_message: str):
        """
        打印醒目的错误日志。
        """
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        logger.error("!!! CRITICAL CONFIGURATION ERROR                            !!!")
        logger.error("!!!                                                         !!!")
        logger.error("!!! SUPABASE_SERVICE_ROLE_KEY is INVALID or has NO PERMISSION !!!")
        logger.error("!!!                                                         !!!")
        logger.error(f"!!! Error: {error_message[:55]:<55} !!!")
        logger.error("!!!                                                         !!!")
        logger.error("!!! Please update the key in your .env file immediately.    !!!")
        logger.error("!!! The application might not function correctly.           !!!")
        logger.error("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

# 创建健康检查服务实例
health_check_service = HealthCheckService() 