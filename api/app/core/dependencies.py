from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Tuple

from app.services import auth_service
from app.schemas import UserResponse
from app.services.supabase_client import supabase_service
from app.core.i18n import SupportedLanguage, get_language_from_header

# HTTP Bearer 安全方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """获取当前用户依赖项"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 直接使用 Supabase 验证 token 并获取用户信息
        user = await auth_service.get_user_by_token(credentials.credentials)
        if user is None:
            raise credentials_exception
            
        return user
        
    except Exception:
        raise credentials_exception


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[UserResponse]:
    """可选的当前用户依赖项（用于某些端点可能需要也可能不需要认证）"""
    if credentials is None:
        return None
        
    try:
        user = await auth_service.get_user_by_token(credentials.credentials)
        return user
        
    except Exception:
        return None


def get_supabase_client():
    """获取 Supabase 客户端依赖项"""
    return supabase_service.get_client()


async def get_current_user_with_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Tuple[UserResponse, str]:
    """获取当前用户和访问令牌"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证身份凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 验证token并获取用户信息
        user = await auth_service.get_user_by_token(credentials.credentials)
        if user is None:
            raise credentials_exception
            
        return user, credentials.credentials
        
    except Exception:
        raise credentials_exception


def get_language(
    accept_language: Optional[str] = Header(None, alias="Accept-Language")
) -> SupportedLanguage:
    """获取请求语言依赖项"""
    return get_language_from_header(accept_language)