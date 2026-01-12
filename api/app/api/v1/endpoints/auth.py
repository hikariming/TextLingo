from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.auth import (
    AuthResponse,
    UserLoginRequest,
    TokenRefreshRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    TokenLoginRequest,
    TokenVerifyRequest,
    UserRegisterRequest,
    UserResponse,
    GoogleOAuthRequest,
    GoogleOAuthResponse,
    GoogleMobileAuthRequest,
    GoogleUserInfo,
    SupabaseOAuthRequest,
    SupabaseOAuthResponse,
    OAuthErrorType,
    OAuthErrorResponse
)
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user
import structlog
import httpx
import secrets
import string
import jwt
from datetime import datetime, timedelta
from app.services.user_service import user_service
from app.core.config import settings
# 临时导入已清理

logger = structlog.get_logger()

router = APIRouter()


@router.post("/register", response_model=AuthResponse, summary="用户注册")
async def register(user_data: UserRegisterRequest):
    """
    用户注册端点
    
    - **email**: 用户邮箱地址
    - **password**: 用户密码（至少6位）
    - **full_name**: 用户昵称（必填，至少2个字符）
    - **native_language**: AI讲解语言（可选，默认为中文）
    
    返回用户信息和访问令牌
    """
    try:
        result = await auth_service.register_user(user_data)
        logger.info(f"User registered successfully: {user_data.email}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=AuthResponse, summary="用户登录")
async def login(login_data: UserLoginRequest):
    """
    用户登录端点
    
    - **email**: 用户邮箱地址
    - **password**: 用户密码
    
    返回用户信息和访问令牌
    """
    try:
        result = await auth_service.login_user(login_data)
        logger.info(f"User logged in successfully: {login_data.email}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    获取当前用户的基础信息
    
    需要在请求头中提供有效的访问令牌：
    Authorization: Bearer <access_token>
    """
    return current_user


@router.post("/refresh", response_model=AuthResponse, summary="刷新访问令牌")
async def refresh_token(refresh_request: TokenRefreshRequest):
    """
    刷新访问令牌端点
    
    - **refresh_token**: 刷新令牌
    
    返回新的访问令牌和刷新令牌
    """
    try:
        result = await auth_service.refresh_access_token(refresh_request)
        logger.info("Token refreshed successfully")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="刷新令牌失败，请稍后重试"
        )


@router.post("/logout", summary="用户登出")
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    用户登出端点
    
    注意：由于使用JWT令牌，客户端需要自行删除令牌
    此端点主要用于记录日志和执行清理操作
    """
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "登出成功"}


@router.post("/forgot-password", response_model=ForgotPasswordResponse, summary="忘记密码")
async def forgot_password(request_data: ForgotPasswordRequest):
    """
    忘记密码端点 - 发送密码重置邮件
    
    - **email**: 用户邮箱地址
    
    返回发送结果（为安全考虑，总是返回成功消息）
    """
    try:
        result = await auth_service.send_reset_password_email(request_data)
        logger.info(f"Password reset email request processed for: {request_data.email}")
        return result
    except Exception as e:
        logger.error(f"Forgot password failed: {e}")
        # 即使出错也返回成功消息，避免暴露系统信息
        return ForgotPasswordResponse(
            success=True,
            message="如果该邮箱地址已注册，您将收到密码重置邮件。请检查您的邮箱（包括垃圾邮件文件夹）。"
        )


@router.post("/reset-password", response_model=PasswordResetResponse, summary="重置密码")
async def reset_password(reset_data: PasswordResetRequest):
    """
    重置用户密码端点
    
    - **access_token**: 从重置邮件链接中获取的access_token
    - **new_password**: 新密码（至少6位）
    - **email**: 用户邮箱地址
    
    返回重置结果
    """
    try:
        result = await auth_service.reset_password(reset_data)
        logger.info(f"Password reset successfully for: {reset_data.email}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置失败，请稍后重试"
        )





@router.post("/token-login", response_model=AuthResponse, summary="跨版本token登录")
async def token_login(token_request: TokenLoginRequest):
    """
    使用textlingo1的token登录到textlingo2系统
    
    - **token**: 来自textlingo1系统的有效token
    
    返回textlingo2系统的用户信息和访问令牌
    """
    try:
        # 请求textlingo1验证token
        textlingo1_api_url = settings.textlingo1_api_url
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{textlingo1_api_url}/api/auth/verify-token",
                    json={"token": token_request.token},
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="token验证失败"
                    )
                
                user_info = response.json()
                email = user_info.get('email')
                username = user_info.get('username') or user_info.get('display_name')
                
                if not email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="无法获取用户邮箱"
                    )
                
                # 检查用户是否在textlingo2系统中存在
                existing_user = await user_service.get_user_by_email(email)
                
                if not existing_user:
                    # 用户不存在，自动创建账户
                    logger.info(f"User {email} not found in TextLingo2, creating new account")
                    
                    # 简化用户创建逻辑
                    # 使用一个固定的、足够复杂的临时密码
                    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16)) + "A1b!"
                    
                    register_data = UserRegisterRequest(
                        email=email,
                        password=temp_password,
                        full_name=username or email.split('@')[0]
                    )
                    
                    # 调用跨版本注册服务，跳过邮箱确认
                    auth_response = await auth_service.register_user_for_cross_version(register_data)
                    logger.info(f"User {email} created and logged in via token-login.")
                    return auth_response

                # 如果用户已存在，直接为他们创建新的jwt
                logger.info(f"Existing user {email} found. Generating new token for them.")
                
                # 由于现有用户，我们生成一个简单的JWT token用于跨版本认证
                now = datetime.now()
                expires_at = now + timedelta(hours=24)
                
                # 创建token payload - 使用cross_version分支获取完整用户信息
                token_payload = {
                    "sub": existing_user['id'],
                    "email": existing_user['email'],
                    "role": "authenticated",  # Supabase角色
                    "exp": int(expires_at.timestamp()),
                    "iat": int(now.timestamp()),
                    "cross_version": True,
                    "user_metadata": {
                        "full_name": existing_user.get('full_name') or username
                    }
                }
                
                # 生成access token
                access_token = jwt.encode(
                    token_payload,
                    settings.jwt_secret_key,
                    algorithm="HS256"
                )
                
                # 为简化，refresh_token暂时设为空字符串
                refresh_token = ""

                return AuthResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=24 * 3600,
                    expires_at=int(expires_at.timestamp()),
                    user=UserResponse(
                        id=existing_user['id'],
                        email=existing_user['email'],
                        full_name=existing_user.get('full_name') or username,
                        email_confirmed_at=existing_user.get('email_confirmed_at'),
                        created_at=existing_user.get('created_at'),
                        updated_at=existing_user.get('updated_at')
                    )
                )
                
            except httpx.RequestError as e:
                logger.error(f"Failed to connect to textlingo1: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="验证服务连接失败"
                )
            
    except HTTPException:
        # 重新抛出已知的HTTP异常
        raise
    except Exception as e:
        # 记录详细的、未捕获的异常信息
        logger.error(f"Cross-version login failed unexpectedly for token: {token_request.token[:30]}... Error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="跨版本登录失败，请稍后重试"
        )


@router.post("/verify-token", summary="验证token")
async def verify_token(token_request: TokenVerifyRequest):
    """
    验证textlingo2的token（供textlingo1调用）
    
    - **token**: 需要验证的token
    
    返回token的有效性和用户信息
    """
    try:
        # 使用现有的get_user_by_token方法验证token
        user = await auth_service.get_user_by_token(token_request.token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="token无效"
            )
        
        return {
            "email": user.email,
            "username": user.full_name,
            "display_name": user.full_name,
            "user_id": user.id,
            "valid": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="token验证失败"
        )


@router.post("/google", response_model=GoogleOAuthResponse, summary="Google OAuth登录")
async def google_oauth_login(oauth_data: GoogleOAuthRequest):
    """
    Google OAuth登录端点 - 使用Supabase会话交换
    
    - **code**: Google OAuth授权码
    
    使用Supabase内置OAuth功能，避免手动处理授权码
    """
    try:
        logger.info(f"🔥 开始处理Google OAuth登录，授权码: {oauth_data.code[:20]}...")
        
        # 使用Supabase的OAuth会话交换功能，而不是手动处理Google API
        auth_response = await auth_service.exchange_oauth_code_for_session(oauth_data.code)
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google OAuth会话创建失败"
            )
        
        user_id = auth_response.user.id
        is_new_user = auth_response.is_new_user
        
        # 获取或创建用户档案
        try:
            user_profile = await user_service.get_user_profile(user_id)
            if not user_profile and is_new_user:
                # 为新用户创建默认档案
                await create_default_user_profile(user_id, auth_response.user)
                user_profile = await user_service.get_user_profile(user_id)
        except Exception as e:
            logger.warning(f"处理用户档案时出错: {e}")
            # 继续处理，即使档案创建失败
            user_profile = None
        
        # 构建响应
        response = GoogleOAuthResponse(
            access_token=auth_response.access_token,
            refresh_token=auth_response.refresh_token,
            expires_in=auth_response.expires_in,
            expires_at=auth_response.expires_at,
            user=auth_response.user,
            user_profile=user_profile,
            is_new_user=is_new_user,
            message="Google登录成功！" if not is_new_user else "欢迎使用TextLingo2！已为您创建新账户。"
        )
        
        logger.info(f"Google OAuth login successful: {auth_response.user.email}, new_user: {is_new_user}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google登录失败，请稍后重试"
        )


@router.post("/google-mobile", response_model=GoogleOAuthResponse, summary="移动端Google登录")
async def google_mobile_login(auth_data: GoogleMobileAuthRequest):
    """
    移动端Google登录端点 - 使用Google access token
    
    - **access_token**: Google Sign In获取的access token
    - **id_token**: Google ID token (可选)
    
    适用于Flutter等移动端应用的Google Sign In流程
    """
    try:
        logger.info(f"🔥 开始处理移动端Google登录...")
        
        # 使用新的移动端Google认证方法
        auth_response = await auth_service.google_mobile_auth(
            auth_data.access_token,
            auth_data.id_token
        )
        
        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google移动端登录失败"
            )
        
        user_id = auth_response.user.id
        is_new_user = auth_response.is_new_user
        
        # 获取用户档案
        try:
            user_profile = await user_service.get_user_profile(user_id)
        except Exception as e:
            logger.warning(f"获取用户档案失败: {e}")
            user_profile = None
        
        # 构建响应
        response = GoogleOAuthResponse(
            access_token=auth_response.access_token,
            refresh_token=auth_response.refresh_token,
            expires_in=auth_response.expires_in,
            expires_at=auth_response.expires_at,
            user=auth_response.user,
            user_profile=user_profile,
            is_new_user=is_new_user,
            message=auth_response.message
        )
        
        logger.info(f"Google移动端登录成功: {auth_response.user.email}, new_user: {is_new_user}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google移动端登录失败: {e}")
        logger.error(f"错误类型: {type(e).__name__}")
        logger.error(f"错误详情: {str(e)}")
        import traceback
        logger.error(f"完整错误追踪: {traceback.format_exc()}")
        # 在调试阶段显示具体错误信息，生产环境应该使用通用错误信息
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google登录失败: {str(e)}"
        )


@router.post("/supabase-oauth", response_model=SupabaseOAuthResponse, summary="Supabase OAuth登录")
async def supabase_oauth_login(oauth_data: SupabaseOAuthRequest):
    """
    Supabase OAuth登录端点 - 使用Supabase token创建后端JWT
    
    - **access_token**: Supabase会话的access_token
    - **user_info**: Supabase用户信息
    
    此端点将验证Supabase token，创建或更新用户档案，并生成后端JWT token
    """
    try:
        logger.info(f"🔥 开始处理Supabase OAuth登录...")
        
        # 调用auth service处理Supabase OAuth
        auth_response = await auth_service.process_supabase_oauth(
            oauth_data.access_token,
            oauth_data.user_info
        )
        
        # 获取用户档案
        try:
            user_profile = await user_service.get_user_profile(auth_response.user.id)
        except Exception as e:
            logger.warning(f"获取用户档案失败: {e}")
            user_profile = None
        
        # 构建Supabase OAuth响应
        response = SupabaseOAuthResponse(
            access_token=auth_response.access_token,
            refresh_token=auth_response.refresh_token,
            expires_in=auth_response.expires_in,
            expires_at=auth_response.expires_at,
            user=auth_response.user,
            user_profile=user_profile,
            is_new_user=auth_response.is_new_user,
            message=auth_response.message
        )
        
        logger.info(f"✅ Supabase OAuth登录成功: {auth_response.user.email}, new_user: {auth_response.is_new_user}")
        return response
        
    except HTTPException as e:
        # 将HTTPException转换为更友好的OAuth错误响应
        error_type, friendly_message, retry_available = map_auth_error_to_oauth_error(e.detail)
        
        logger.error(f"❌ Supabase OAuth登录失败: {e.detail}")
        
        raise HTTPException(
            status_code=e.status_code,
            detail={
                "error_type": error_type,
                "error_code": e.detail,
                "message": friendly_message,
                "retry_available": retry_available
            }
        )
    except Exception as e:
        logger.error(f"💥 Supabase OAuth登录异常: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_type": OAuthErrorType.UNKNOWN_ERROR,
                "error_code": "unknown_error",
                "message": "登录过程中发生未知错误，请稍后重试",
                "retry_available": True
            }
        )


def map_auth_error_to_oauth_error(error_detail) -> tuple[OAuthErrorType, str, bool]:
    """
    将认证错误映射为OAuth错误类型和友好消息
    
    Args:
        error_detail: 错误详情，可能是字符串或字典
    
    Returns:
        tuple: (error_type, friendly_message, retry_available)
    """
    # 处理字典类型的error_detail
    if isinstance(error_detail, dict):
        error_code = error_detail.get('error_code') or error_detail.get('error_type', 'unknown_error')
        error_message = error_detail.get('message', '未知错误')
    else:
        # 字符串类型
        error_code = str(error_detail) if error_detail else 'unknown_error'
        error_message = error_code
    
    # 检查具体错误内容以提供更准确的错误类型
    error_str = str(error_message).lower()
    
    # 时序和数据库相关错误
    if 'not present in table "users"' in error_str or 'foreign key constraint' in error_str:
        return (
            OAuthErrorType.PROFILE_CREATION_FAILED,
            "用户创建过程中出现时序问题，请稍等片刻后重试",
            True
        )
    
    # RLS权限错误
    if 'violates row-level security' in error_str or 'rls' in error_str:
        return (
            OAuthErrorType.PROFILE_CREATION_FAILED,
            "权限验证失败，请稍后重试或联系技术支持",
            True
        )
    
    # 重试次数用完的错误
    if '重试次数已用完' in error_str or '重试' in error_str:
        return (
            OAuthErrorType.PROFILE_CREATION_FAILED,
            "档案创建暂时失败，建议稍后重新登录",
            True
        )
    
    error_mappings = {
        "invalid_token": (
            OAuthErrorType.INVALID_TOKEN,
            "登录凭证无效，请重新登录",
            True
        ),
        "expired_token": (
            OAuthErrorType.EXPIRED_TOKEN,
            "登录凭证已过期，请重新登录",
            True
        ),
        "profile_creation_failed": (
            OAuthErrorType.PROFILE_CREATION_FAILED,
            "用户档案创建失败，建议稍后重试",
            True
        ),
        "token_creation_failed": (
            OAuthErrorType.USER_CREATION_FAILED,
            "登录令牌创建失败，请稍后重试",
            True
        ),
        "network_error": (
            OAuthErrorType.NETWORK_ERROR,
            "网络连接失败，请检查网络后重试",
            True
        )
    }
    
    return error_mappings.get(
        error_code,
        (OAuthErrorType.UNKNOWN_ERROR, f"登录过程中出现问题：{error_message}，请稍后重试", True)
    )


async def create_default_user_profile(user_id: str, user: UserResponse):
    """为新的Google用户创建默认档案"""
    try:
        user_metadata = user.user_metadata if hasattr(user, 'user_metadata') else {}
        full_name = user_metadata.get('full_name', '') or user.full_name or ''
        avatar_url = user_metadata.get('avatar_url')
        
        # 根据Google账户locale推断语言偏好
        locale = user_metadata.get('locale', 'zh')
        native_language = 'zh'
        if locale:
            if locale.startswith('en'):
                native_language = 'en'
            elif locale.startswith('ja'):
                native_language = 'ja'
            elif locale.startswith('ko'):
                native_language = 'ko'
        
        profile_data = {
            'user_id': user_id,
            # 移除了 'email': user.email, 因为user_profiles表中没有email字段
            'full_name': full_name,
            'avatar_url': avatar_url,
            'role': 'free',
            'points': 350,  # 新用户赠送积分
            'native_language': native_language,
            'learning_language': 'en' if native_language != 'en' else 'zh',
            'language_level': 'beginner'
            # 移除了interface_language, plan_type, subscription_status等user_profiles表中不存在的字段
        }
        
        supabase = auth_service.supabase
        supabase.table('user_profiles').insert(profile_data).execute()
        logger.info(f"Created default profile for Google user: {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to create default profile for user {user_id}: {e}")
        # 不抛出异常，让登录流程继续


# 移除旧的Google用户信息获取函数，改用Supabase内置方法
# async def get_google_user_info(auth_code: str) -> dict:
#     这个函数导致了invalid_grant错误，已被替换 

# 调试接口已移除 - 问题已解决 