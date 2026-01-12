"""
本地JWT认证模块 - 高性能、可靠的Supabase token验证
避免网络调用的不稳定性，提供极速的本地JWT验证
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Dict, Any, Tuple, Optional
from app.core.config import settings
from app.schemas.auth import UserResponse
from datetime import datetime
import uuid
import structlog

logger = structlog.get_logger()
security = HTTPBearer()

def decode_supabase_jwt(token: str) -> Dict[str, Any]:
    """
    本地验证Supabase JWT token - 极速且可靠
    不依赖网络调用，避免间歇性认证失败
    """
    try:
        # 使用Supabase的JWT secret进行本地验证
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_exp": True}
        )
        
        # 验证必需字段
        if not payload.get("sub") or not payload.get("email"):
            raise jwt.InvalidTokenError("Token缺少必需字段")
            
        logger.debug("JWT token本地验证成功")
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token已过期")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.debug(f"JWT token无效: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"JWT解码异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token verification failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_with_token_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Tuple[UserResponse, str]:
    """
    基于本地JWT验证获取当前用户和访问令牌
    极速且可靠，不依赖网络调用
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated"
        )
        
    token = credentials.credentials
    
    try:
        # 使用本地JWT验证（不发起网络请求）
        payload = decode_supabase_jwt(token)
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token缺少必需的用户信息"
            )
        
        # 安全地处理时间戳
        def safe_parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                # 处理多种Supabase时间格式
                if dt_str.endswith('Z'):
                    dt_str = dt_str[:-1] + '+00:00'
                elif '+' not in dt_str and 'T' in dt_str:
                    dt_str = dt_str + '+00:00'
                return datetime.fromisoformat(dt_str)
            except:
                return None

        user_metadata = payload.get("user_metadata", {})
        
        user = UserResponse(
            id=user_id,  # Supabase用户ID是字符串，不需要转换为UUID
            email=email,
            full_name=user_metadata.get("full_name"),
            email_confirmed_at=safe_parse_datetime(payload.get("email_confirmed_at")),
            created_at=safe_parse_datetime(payload.get("created_at")),
            updated_at=safe_parse_datetime(payload.get("updated_at"))
        )
        
        logger.debug(f"本地JWT认证成功: {email}")
        return user, token
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"JWT认证依赖异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def extract_user_info_from_jwt(payload: Dict[str, Any]) -> UserResponse:
    """从JWT payload提取用户信息，用于auth_service"""
    try:
        user_metadata = payload.get("user_metadata", {})
        
        def safe_parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
            if not dt_str:
                return None
            try:
                if dt_str.endswith('Z'):
                    dt_str = dt_str[:-1] + '+00:00'
                elif '+' not in dt_str and 'T' in dt_str:
                    dt_str = dt_str + '+00:00'
                return datetime.fromisoformat(dt_str)
            except:
                return None
        
        return UserResponse(
            id=payload.get("sub"),
            email=payload.get("email"),
            full_name=user_metadata.get("full_name"),
            email_confirmed_at=safe_parse_datetime(payload.get("email_confirmed_at")),
            created_at=safe_parse_datetime(payload.get("created_at")),
            updated_at=safe_parse_datetime(payload.get("updated_at"))
        )
    except Exception as e:
        logger.error(f"提取JWT用户信息失败: {e}")
        raise ValueError(f"Invalid JWT payload: {e}")

# 全局JWT认证函数，供其他模块调用
def verify_supabase_token_locally(token: str) -> Optional[UserResponse]:
    """
    本地验证Supabase token并返回用户信息
    用于auth_service中替代网络调用
    """
    try:
        payload = decode_supabase_jwt(token)
        return extract_user_info_from_jwt(payload)
    except HTTPException:
        # JWT验证失败
        return None
    except Exception as e:
        logger.error(f"本地token验证异常: {e}")
        return None 