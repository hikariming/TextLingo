from supabase import create_client, Client, ClientOptions
from gotrue import SyncGoTrueClient
from app.core.config import settings
import structlog

logger = structlog.get_logger()


class SupabaseService:
    """Supabase 服务类"""
    
    def __init__(self):
        self.service_client: Client = None  # Service role客户端(绕过RLS)
        self.anon_client: Client = None     # 匿名客户端(支持RLS)
        self.auth_client: SyncGoTrueClient = None
        self._initialize_clients()
    
    def _initialize_clients(self):
        """初始化 Supabase 客户端"""
        try:
            # Service role客户端 - 用于管理操作，绕过RLS
            self.service_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_service_role_key
            )
            
            # 匿名客户端 - 用于普通业务操作，遵循RLS策略
            self.anon_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key
            )
            
            self.auth_client = self.service_client.auth
            logger.info("Supabase clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase clients: {e}")
            raise
    
    def get_client(self) -> Client:
        """获取 Service Role 客户端（绕过RLS，用于管理操作）"""
        # 修复: 每次调用都创建一个新的 service_role 客户端实例，
        # 以防止长连接的会话状态失效。
        # 这是一个解决 "403 Forbidden" 错误的最佳实践。
        logger.debug("Creating a new Supabase service_role client instance...")
        return create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_role_key
        )
    
    def get_user_client(self, access_token: str = None) -> Client:
        """获取用户客户端（遵循RLS策略）"""
        if access_token:
            # 创建临时客户端并手动设置Authorization header
            # 使用ClientOptions对象而不是字典
            options = ClientOptions(
                headers={
                    "Authorization": f"Bearer {access_token}"
                }
            )
            user_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key,
                options=options
            )
            return user_client
        return self.anon_client
    
    def get_auth_client(self) -> SyncGoTrueClient:
        """获取认证客户端"""
        return self.auth_client


# 创建全局 Supabase 服务实例
supabase_service = SupabaseService() 