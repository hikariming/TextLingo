from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from gotrue.errors import AuthApiError

from app.core.config import settings
from app.services.supabase_client import supabase_service
from app.schemas import UserRegisterRequest, UserLoginRequest, UserResponse, AuthResponse, TokenRefreshRequest, PasswordResetRequest, PasswordResetResponse, ForgotPasswordRequest, ForgotPasswordResponse
import structlog
import jwt

logger = structlog.get_logger()


class AuthService:
    """认证服务类"""
    
    def __init__(self):
        self.supabase = supabase_service.get_client()
        self.auth_client = supabase_service.get_auth_client()
    
    async def validate_user_exists_in_auth(self, user_id: str) -> bool:
        """验证用户是否存在于auth.users表中"""
        try:
            # 使用admin API检查用户是否存在
            user_response = self.supabase.auth.admin.get_user_by_id(user_id)
            
            # 检查响应是否包含用户数据
            if hasattr(user_response, 'user') and user_response.user:
                logger.debug(f"User {user_id} exists in auth.users")
                return True
            elif hasattr(user_response, 'id') and user_response.id:
                # 有些情况下用户对象直接返回
                logger.debug(f"User {user_id} exists in auth.users")
                return True
            else:
                logger.warning(f"User {user_id} not found in auth.users")
                return False
                
        except Exception as e:
            logger.error(f"Error checking user existence for {user_id}: {e}")
            # 如果检查失败，假设用户不存在以避免外键约束错误
            return False
    
    async def create_user_profile_with_retry(self, user_id: str, profile_data: dict, max_retries: int = 3) -> bool:
        """使用指数退避重试机制创建用户档案"""
        import asyncio
        
        logger.info(f"🔄 Starting to create user profile for {user_id}, maximum {max_retries} retries")
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 Attempt {attempt + 1}/{max_retries} to create profile")
                
                # 在重试前验证用户是否存在
                if attempt > 0:
                    user_exists = await self.validate_user_exists_in_auth(user_id)
                    if not user_exists:
                        logger.warning(f"⚠️ Attempt {attempt + 1}: user {user_id} still not in auth.users")
                        # 等待更长时间让auth用户完全创建
                        delay = 2.0 * (2 ** attempt)  # 指数退避: 2s, 4s, 8s
                        logger.info(f"⏰ Waiting {delay}s before retrying...")
                        await asyncio.sleep(delay)
                        continue
                
                # 方法1: 尝试使用 RPC 调用绕过 RLS 策略
                try:
                    logger.info(f"🔧 Attempting to create profile using RPC function")
                    
                    # 确保所有必要的参数都存在
                    rpc_params = {
                        'p_user_id': user_id,
                        'p_role': profile_data.get('role', 'free'),
                        'p_points': profile_data.get('points', 350),
                        'p_native_language': profile_data.get('native_language', 'zh'),
                        'p_full_name': profile_data.get('full_name'),
                        'p_learning_language': profile_data.get('learning_language', 'en'),
                        'p_language_level': profile_data.get('language_level', 'beginner'),
                        'p_avatar_url': profile_data.get('avatar_url'),
                        'p_bio': profile_data.get('bio'),
                        'p_profile_setup_completed': profile_data.get('profile_setup_completed', False)
                    }
                    
                    logger.info(f"📊 RPC参数: {rpc_params}")
                    
                    profile_response = self.supabase.rpc('create_user_profile_bypass_rls', rpc_params).execute()
                    
                    # 验证RPC响应
                    if hasattr(profile_response, 'data') and profile_response.data:
                        logger.info(f"✅ RPC profile creation successful, attempt {attempt + 1}")
                        return True
                    else:
                        raise Exception("RPC call returned empty result")
                        
                except Exception as rpc_error:
                    logger.warning(f"⚠️ RPC method failed, attempt {attempt + 1}: {rpc_error}")
                    
                    # 方法2: 回退到使用Service Role Key直接插入
                    try:
                        logger.info(f"🔄 Attempting to create profile using Service Role directly")
                        
                        # 使用统一的service role客户端
                        from app.services.supabase_client import supabase_service
                        service_client = supabase_service.get_client()
                        
                        profile_response = service_client.table('user_profiles').insert(profile_data).execute()
                        
                        if not hasattr(profile_response, 'data') or not profile_response.data:
                            raise Exception("Profile creation failed: database returned empty result")
                        
                        logger.info(f"✅ Direct insert profile creation successful, attempt {attempt + 1}")
                        return True
                        
                    except Exception as direct_error:
                        logger.error(f"❌ Direct insert failed, attempt {attempt + 1}: {direct_error}")
                        
                        # 如果是外键约束错误且还有重试机会，继续重试
                        if 'violates foreign key constraint' in str(direct_error) and attempt < max_retries - 1:
                            delay = 2.0 * (2 ** attempt)  # 指数退避: 2s, 4s, 8s
                            logger.info(f"🔄 Foreign key constraint conflict, {delay}s before retrying...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            # 重新抛出错误
                            raise direct_error
                            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Profile creation attempt {attempt + 1} failed: {e}")
                logger.error(f"❌ Error type: {type(e).__name__}")
                
                # 分析具体错误原因
                if 'not present in table "users"' in error_msg:
                    logger.error(f"❌ Foreign key constraint error: user {user_id} not in auth.users")
                elif 'violates row-level security' in error_msg:
                    logger.error(f"❌ RLS policy prevents profile creation")
                elif 'duplicate key value' in error_msg:
                    logger.warning(f"⚠️ Profile already exists, creation successful")
                    return True  # Profile already exists, considered successful
                
                # 如果是最后一次尝试，抛出错误
                if attempt == max_retries - 1:
                    logger.error(f"❌ All {max_retries} attempts failed, giving up profile creation")
                    raise e
                
                # 否则等待后重试
                delay = 2.0 * (2 ** attempt)  # 指数退避: 2s, 4s, 8s
                logger.info(f"⏰ Waiting {delay}s before retrying profile creation...")
                await asyncio.sleep(delay)
        
        logger.error(f"❌ Profile creation completely failed")
        return False
    
    async def register_user(self, user_data: UserRegisterRequest) -> AuthResponse:
        """User registration"""
        registration_context = {
            "email": user_data.email,
            "native_language": user_data.native_language,
            "full_name": user_data.full_name
        }
        
        logger.info("Starting user registration", extra=registration_context)
        
        try:
            # 使用 Supabase Auth 注册用户
            logger.info("Calling Supabase sign_up", extra=registration_context)
            response = self.auth_client.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name
                    }
                }
            })
            
            # 详细的响应日志
            auth_response_context = {
                **registration_context,
                "has_user": bool(response.user),
                "has_session": bool(response.session),
                "user_id": response.user.id if response.user else None
            }
            logger.info("Supabase sign_up completed", extra=auth_response_context)
            
            if response.user:
                logger.info(f"Auth user created successfully: {response.user.id}", extra={
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "email_confirmed": bool(response.user.email_confirmed_at)
                })
            if response.session:
                logger.info("Session created with access token", extra={
                    "user_id": response.user.id if response.user else None,
                    "has_access_token": bool(response.session.access_token),
                    "expires_in": response.session.expires_in
                })
            
            if not response.user:
                logger.error("Supabase sign_up failed: no user returned", extra=registration_context)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User creation failed"
                )

            # 为新用户创建个人资料，并设置默认角色和积分
            # 修改：如果档案创建失败，则注册失败
            try:
                profile_data = {
                    'user_id': response.user.id,
                    'email': response.user.email,  # 添加缺失字段
                    'role': 'free',
                    'points': 350,
                    'native_language': user_data.native_language or 'zh',
                    'full_name': user_data.full_name,
                    'learning_language': 'en' if (user_data.native_language or 'zh') != 'en' else 'zh',
                    'language_level': 'beginner',
                    'bio': '',  # 添加缺失字段
                    'avatar_url': None,  # 添加缺失字段
                    'profile_setup_completed': True  # 普通注册用户设置为已完成
                }
                
                # 使用重试机制创建用户档案
                success = await self.create_user_profile_with_retry(response.user.id, profile_data)
                
                if not success:
                    raise Exception("User profile creation failed: retry attempts exhausted")
                
            except Exception as e:
                # 修复：如果档案创建失败，不要删除用户，而是记录错误并允许后续重试
                profile_error_context = {
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "profile_data": profile_data
                }
                logger.error("Profile creation failed after retries", extra=profile_error_context)
                
                # 分类错误类型并提供相应的处理
                error_message = str(e).lower()
                
                if 'not present in table "users"' in error_message or 'violates foreign key constraint' in error_message:
                    logger.error("Foreign key constraint violation - timing issue detected", extra={
                        "user_id": response.user.id,
                        "error_category": "foreign_key_constraint",
                        "suggested_action": "retry_registration"
                    })
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Timing issue occurred during user creation, please try registering again"
                    )
                elif 'violates row-level security' in error_message:
                    logger.error("RLS policy violation", extra={
                        "user_id": response.user.id,
                        "error_category": "rls_policy",
                        "suggested_action": "retry_login"
                    })
                    # Don't delete user, allow user to exist but with missing profile, can be supplemented later
                    logger.info(f"User {response.user.id} created but profile creation failed due to RLS. User can retry login.")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="User created successfully but profile setup failed, please try logging in again later"
                    )
                elif 'headers' in error_message or 'attribute' in error_message:
                    logger.error("Supabase client response handling error", extra={
                        "user_id": response.user.id,
                        "error_category": "client_response",
                        "suggested_action": "retry_login"
                    })
                    logger.info(f"User {response.user.id} exists but profile creation failed due to client error. User can retry login.")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="User created successfully but profile setup failed, please try logging in again later"
                    )
                else:
                    # 其他未分类错误
                    logger.error("Unclassified profile creation error", extra={
                        "user_id": response.user.id,
                        "error_category": "unknown",
                        "suggested_action": "retry_login",
                        "full_error": str(e)
                    })
                    logger.info(f"User {response.user.id} exists but profile missing. Can be created on next login attempt.")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="User created successfully but profile setup failed, please try logging in again later"
                    )

            # 检查是否需要邮箱确认
            if not response.session:
                # 邮箱确认模式 - 返回特殊响应
                logger.info(f"User registered successfully, email confirmation required: {response.user.email}")
                return AuthResponse(
                    access_token="",  # 空token表示需要邮箱确认
                    refresh_token="",
                    expires_in=0,
                    expires_at=0,
                    user=UserResponse(
                        id=response.user.id,
                        email=response.user.email,
                        full_name=user_data.full_name,
                        email_confirmed_at=response.user.email_confirmed_at,
                        created_at=response.user.created_at,
                        updated_at=response.user.updated_at
                    ),
                    message="Registration successful! Please check your email and click the confirmation link, then return to the homepage and log in again."
                )

            # 正常情况 - 有session的注册
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=user_data.full_name,
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
            
            expires_at = int(datetime.now().timestamp()) + (response.session.expires_in or 3600)
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in or 3600,
                expires_at=expires_at,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as auth_error:
            # 打印更详细的错误信息
            logger.error(f"Registration error details: {auth_error}")
            logger.error(f"Error type: {type(auth_error)}")
            
            # 检查是否有error属性
            if hasattr(auth_error, 'error'):
                logger.error(f"Supabase error: {auth_error.error}")
            if hasattr(auth_error, 'message'):
                logger.error(f"Supabase message: {auth_error.message}")
            if hasattr(auth_error, 'details'):
                logger.error(f"Supabase details: {auth_error.details}")
            
            if "AuthError" in str(type(auth_error)) or "Auth" in str(auth_error):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Registration failed: {str(auth_error)}"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Server internal error: {str(auth_error)}"
            )
    
    async def login_user(self, login_data: UserLoginRequest) -> AuthResponse:
        """User login"""
        try:
            # 使用 Supabase Auth 登录
            response = self.auth_client.sign_in_with_password({
                "email": login_data.email,
                "password": login_data.password
            })
            
            if not response.user or not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Email or password incorrect"
                )
            
            # 创建用户响应对象
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=response.user.user_metadata.get("full_name"),
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
            
            expires_at = int(datetime.now().timestamp()) + (response.session.expires_in or 3600)
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in or 3600,
                expires_at=expires_at,
                user=user_response
            )
            
        except AuthApiError as auth_error:
            logger.error(f"Supabase login error: {auth_error.message}")
            if "Email not confirmed" in auth_error.message:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="email_not_confirmed"
                )
            elif "Invalid login credentials" in auth_error.message:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_credentials"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_credentials"  # 默认为凭据无效
                )
        except Exception as e:
            logger.error(f"Login error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server internal error"
            )
    
    async def refresh_access_token(self, refresh_request: TokenRefreshRequest) -> AuthResponse:
        """Refresh access token - supports Supabase refresh token"""
        try:
            logger.info("🔄 Starting to refresh Supabase token...")
            
            # 使用 Supabase 刷新 token
            response = self.auth_client.refresh_session(refresh_request.refresh_token)
            
            if not response.user or not response.session:
                logger.error("❌ Supabase refresh session returned empty result")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token invalid"
                )
            
            logger.info(f"✅ Supabase token refresh successful: {response.user.email}")
            
            # 创建用户响应对象
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=response.user.user_metadata.get("full_name"),
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
            
            expires_at = int(datetime.now().timestamp()) + (response.session.expires_in or 3600)
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in or 3600,
                expires_at=expires_at,
                user=user_response
            )
            
        except HTTPException:
            raise
        except Exception as auth_error:
            logger.error(f"💥 Supabase token refresh failed: {auth_error}")
            
            # 更具体的错误处理
            error_str = str(auth_error).lower()
            if "invalid" in error_str or "expired" in error_str or "unauthorized" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="刷新令牌已过期或无效，请重新登录"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="刷新令牌失败，请稍后重试"
                )

    async def get_user_by_token(self, token: str) -> Optional[UserResponse]:
        """通过 token 获取用户信息 - 改进版：使用重试机制提高网络验证可靠性"""
        try:
            logger.debug(f"🔍 开始token验证...")
            
            # 改进的Supabase网络验证：使用重试机制
            import asyncio
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.supabase.auth.get_user(token)
                    
                    if response.user:
                        logger.debug(f"✅ Supabase网络验证成功: {response.user.email} (attempt {attempt+1})")
                        return UserResponse(
                            id=response.user.id,
                            email=response.user.email,
                            full_name=response.user.user_metadata.get("full_name"),
                            email_confirmed_at=response.user.email_confirmed_at,
                            created_at=response.user.created_at,
                            updated_at=response.user.updated_at
                        )
                except Exception as e:
                    logger.debug(f"🔄 Supabase网络验证尝试 {attempt+1} 失败: {e}")
                    if attempt < max_retries - 1:
                        # 短暂等待后重试
                        await asyncio.sleep(0.1 * (attempt + 1))  # 递增延迟: 0.1s, 0.2s, 0.3s
                        continue
                    else:
                        # 最后一次尝试失败，继续到下一个验证方法
                        break
            
            # 备选方案：尝试验证自定义 JWT token（用于跨版本登录等）
            try:
                import jwt
                payload = jwt.decode(
                    token, 
                    settings.jwt_secret_key, 
                    algorithms=[settings.jwt_algorithm]
                )
                
                # 获取用户ID和邮箱
                user_id = payload.get('sub')
                email = payload.get('email')
                
                if user_id and email:
                    logger.debug(f"✅ 自定义JWT验证成功: {email}")
                    
                    # 检查这是否是跨版本登录的token
                    if payload.get('cross_version'):
                        # 跨版本登录token，从Supabase获取完整信息
                        try:
                            user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                            user_obj = user_response.user if hasattr(user_response, 'user') else user_response
                                
                            if user_obj:
                                return UserResponse(
                                    id=user_obj.id,
                                    email=user_obj.email,
                                    full_name=user_obj.user_metadata.get("full_name") if user_obj.user_metadata else None,
                                    email_confirmed_at=user_obj.email_confirmed_at,
                                    created_at=user_obj.created_at,
                                    updated_at=user_obj.updated_at
                                )
                        except Exception as e:
                            logger.warning(f"⚠️ 跨版本token Supabase查询失败: {e}")
                            # 返回token中的基本信息
                            return UserResponse(
                                id=user_id,
                                email=email,
                                full_name=None,
                                email_confirmed_at=None,
                                created_at=None,
                                updated_at=None
                            )
                    else:
                        # 普通自定义JWT，从payload构建用户信息
                        user_metadata = payload.get('user_metadata', {})
                        return UserResponse(
                            id=user_id,
                            email=email,
                            full_name=user_metadata.get("full_name"),
                            email_confirmed_at=None,
                            created_at=None,
                            updated_at=None
                        )
                        
            except jwt.ExpiredSignatureError:
                logger.error("⏰ JWT token已过期")
                return None
            except jwt.InvalidTokenError:
                logger.debug("🚫 JWT token格式无效")
                return None
            
            logger.warning(f"❌ 无法验证token")
            return None
            
        except Exception as e:
            logger.error(f"💥 Token验证异常: {e}")
            return None
    
    async def reset_password(self, reset_data: PasswordResetRequest) -> PasswordResetResponse:
        """重置用户密码 - 避开admin API，使用session方法（Supabase官方推荐）"""
        try:
            # Step 1: 验证6位数字token并获取session
            response = self.auth_client.verify_otp({
                "email": reset_data.email,
                "token": reset_data.access_token,
                "type": "recovery"
            })
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="验证码无效或已过期"
                )
            
            # Step 2: 检查是否有有效的session（这是关键）
            if not response.session or not response.session.access_token:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="验证成功但未获得有效session，请重试"
                )
            
            # Step 3: 使用session token创建临时客户端更新密码
            from supabase import create_client
            
            # 创建新客户端，使用用户的session token
            temp_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key  # 使用anon key，不是service role
            )
            
            # 设置用户session
            temp_client.auth.set_session(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token or ""
            )
            
            # Step 4: 现在以用户身份更新密码（不是管理员操作）
            update_response = temp_client.auth.update_user({
                "password": reset_data.new_password
            })
            
            if not update_response.user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="密码更新失败"
                )
            
            logger.info(f"Password reset successful for user: {reset_data.email}")
            
            return PasswordResetResponse(
                success=True,
                message="密码重置成功，请使用新密码登录"
            )

        except AuthApiError as e:
            logger.error(f"Supabase Auth API error during password reset: {e.message}")
            
            error_message_lower = e.message.lower()

            if "invalid" in error_message_lower or "expired" in error_message_lower or "token" in error_message_lower:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="验证码无效或已过期"
                )
            if "user not found" in error_message_lower:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="用户不存在"
                )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"密码重置失败: {e.message}"
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during password reset: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="密码重置失败，请稍后重试"
            )
    
    async def send_reset_password_email(self, request_data: ForgotPasswordRequest) -> ForgotPasswordResponse:
        """发送重置密码邮件"""
        try:
            # 使用Supabase发送重置密码邮件
            response = self.auth_client.reset_password_email(
                request_data.email,
                {
                    "redirect_to": f"{settings.site_url}/auth/reset-password"
                }
            )
            
            # Supabase的reset_password_email方法通常不会抛出异常，即使邮箱不存在
            # 这是为了安全考虑，避免泄露用户是否存在的信息
            
            logger.info(f"Password reset email sent to: {request_data.email}")
            
            return ForgotPasswordResponse(
                success=True,
                message="如果该邮箱地址已注册，您将收到密码重置邮件。请检查您的邮箱（包括垃圾邮件文件夹）。"
            )
            
        except Exception as e:
            logger.error(f"Send reset password email error: {e}")
            
            # 即使发生错误，也返回成功消息，避免暴露系统信息
            return ForgotPasswordResponse(
                success=True,
                message="如果该邮箱地址已注册，您将收到密码重置邮件。请检查您的邮箱（包括垃圾邮件文件夹）。"
            )

    async def register_user_for_cross_version(self, user_data: UserRegisterRequest) -> AuthResponse:
        """
        跨版本登录时的用户注册 - 跳过邮箱确认
        专门用于从textlingo1迁移到textlingo2的用户
        """
        try:
            # 使用 Supabase Auth 注册用户，但不要求邮箱确认
            response = self.auth_client.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name
                    },
                    "email_confirm": False  # 跳过邮箱确认
                }
            })
            
            logger.info(f"Cross-version user registration: user={bool(response.user)}, session={bool(response.session)}")
            
            if not response.user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="跨版本用户创建失败"
                )

            # 创建用户档案
            try:
                profile_data = {
                    'user_id': response.user.id,
                    'email': response.user.email,  # 添加缺失字段
                    'role': 'free',
                    'points': 350,
                    'native_language': user_data.native_language or 'zh',
                    'full_name': user_data.full_name,  # 添加缺失字段
                    'learning_language': 'en' if (user_data.native_language or 'zh') != 'en' else 'zh',  # 添加缺失字段
                    'language_level': 'beginner',  # 添加缺失字段
                    'bio': '',  # 添加缺失字段
                    'avatar_url': None,  # 添加缺失字段
                    'profile_setup_completed': True  # 添加缺失字段
                }
                
                # 使用service role客户端
                from app.services.supabase_client import supabase_service
                service_client = supabase_service.get_client()
                service_client.table('user_profiles').insert(profile_data).execute()
                logger.info(f"Profile created for cross-version user: {response.user.email}")
            except Exception as e:
                logger.warning(f"Failed to create profile for cross-version user {response.user.id}: {e}")

            # 如果没有session（邮箱确认模式），手动创建JWT token
            if not response.session:
                logger.info(f"No session returned, creating manual JWT for cross-version user: {response.user.email}")
                
                # 手动创建JWT token
                now = datetime.now()
                expires_at = now + timedelta(hours=24)
                
                token_payload = {
                    "sub": response.user.id,
                    "email": response.user.email,
                    "role": "authenticated",
                    "exp": int(expires_at.timestamp()),
                    "iat": int(now.timestamp()),
                    "cross_version": True,
                    "user_metadata": {
                        "full_name": user_data.full_name
                    }
                }
                
                access_token = jwt.encode(
                    token_payload,
                    settings.jwt_secret_key,
                    algorithm="HS256"
                )
                
                return AuthResponse(
                    access_token=access_token,
                    refresh_token="",
                    expires_in=24 * 3600,
                    expires_at=int(expires_at.timestamp()),
                    user=UserResponse(
                        id=response.user.id,
                        email=response.user.email,
                        full_name=user_data.full_name,
                        email_confirmed_at=response.user.email_confirmed_at,
                        created_at=response.user.created_at,
                        updated_at=response.user.updated_at
                    ),
                    message="跨版本用户创建成功，请稍后登录邮箱确认注册信息"
                )

            # 有session的正常情况
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=user_data.full_name,
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
            
            expires_at = int(datetime.now().timestamp()) + (response.session.expires_in or 3600)
            
            return AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in or 3600,
                expires_at=expires_at,
                user=user_response,
                message="跨版本用户创建成功"
            )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Cross-version user registration failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="跨版本用户注册失败，请稍后重试"
            )

    async def google_oauth_login(self, google_user_info: dict) -> tuple[str, bool]:
        """
        处理Google OAuth登录
        
        Args:
            google_user_info: Google用户信息
            
        Returns:
            tuple: (user_id, is_new_user)
        """
        try:
            email = google_user_info.get('email')
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google账户缺少邮箱信息"
                )

            # 查找现有用户
            existing_user_response = self.supabase.table('user_profiles').select("*").eq('email', email).execute()
            
            if existing_user_response.data:
                # 用户已存在，直接返回
                user_profile = existing_user_response.data[0]
                logger.info(f"Existing Google user logged in: {email}")
                return user_profile['user_id'], False
            
            # 新用户，需要创建
            full_name = google_user_info.get('name', '')
            avatar_url = google_user_info.get('picture')
            locale = google_user_info.get('locale', 'zh')
            
            # 根据locale设置默认语言
            native_language = 'zh'
            if locale:
                if locale.startswith('en'):
                    native_language = 'en'
                elif locale.startswith('ja'):
                    native_language = 'ja'
                elif locale.startswith('ko'):
                    native_language = 'ko'
            
            # 使用Supabase Auth创建Google用户
            # 由于是OAuth，我们需要使用Supabase的admin方法
            user_data = {
                'email': email,
                'email_confirm': True,  # Google用户邮箱已验证
                'user_metadata': {
                    'full_name': full_name,
                    'avatar_url': avatar_url,
                    'provider': 'google'
                }
            }
            
            # 创建用户
            auth_response = self.supabase.auth.admin.create_user(user_data)
            
            if not auth_response.user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="创建Google用户失败"
                )
            
            user_id = auth_response.user.id
            
            # 创建用户资料，添加所有必需字段
            profile_data = {
                'user_id': user_id,
                'email': email,  # 添加回email字段
                'full_name': full_name,
                'avatar_url': avatar_url,
                'bio': '',  # 添加缺失字段
                'role': 'free',
                'points': 350,  # 新用户赠送积分
                'native_language': native_language,
                'learning_language': 'en' if native_language != 'en' else 'zh',
                'language_level': 'beginner',
                'profile_setup_completed': False  # Google用户需要确认设置
            }
            
            # 使用service role客户端
            from app.services.supabase_client import supabase_service
            service_client = supabase_service.get_client()
            service_client.table('user_profiles').insert(profile_data).execute()
            
            logger.info(f"New Google user created: {email}")
            return user_id, True
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Google OAuth login failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google登录失败，请稍后重试"
            )

    async def create_session_for_user(self, user_id: str) -> dict:
        """
        为用户创建登录会话
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 包含access_token等信息的会话数据
        """
        try:
            # 生成JWT token
            now = datetime.utcnow()
            expires_in = settings.access_token_expire_minutes * 60
            expires_at = int(now.timestamp()) + expires_in
            
            payload = {
                "sub": user_id,
                "exp": expires_at,
                "iat": int(now.timestamp()),
                "type": "access"
            }
            
            access_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
            
            # 生成refresh token
            refresh_payload = {
                "sub": user_id,
                "exp": int((now + timedelta(days=settings.refresh_token_expire_days)).timestamp()),
                "iat": int(now.timestamp()),
                "type": "refresh"
            }
            
            refresh_token = jwt.encode(refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expires_in": expires_in,
                "expires_at": expires_at,
                "token_type": "bearer"
            }
            
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="会话创建失败"
            )

    async def exchange_oauth_code_for_session(self, auth_code: str) -> AuthResponse:
        """
        使用Supabase内置OAuth功能交换授权码为会话
        这是推荐的方式，避免手动处理Google API导致的invalid_grant错误
        
        Args:
            auth_code: OAuth授权码
            
        Returns:
            AuthResponse: 包含会话信息和用户数据
        """
        try:
            logger.info("🔄 使用Supabase OAuth会话交换...")
            
            # 使用Supabase的内置方法交换授权码为会话
            # 这避免了手动调用Google API可能导致的授权码重复使用问题
            response = self.auth_client.exchange_code_for_session({
                "auth_code": auth_code
            })
            
            if not response.user or not response.session:
                logger.error("❌ Supabase OAuth会话交换失败")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google OAuth会话创建失败"
                )
            
            logger.info(f"✅ OAuth会话交换成功: {response.user.email}")
            
            # 检查用户是否是新用户
            is_new_user = await self._is_new_user(response.user.id)
            
            # 如果是新用户，创建用户档案
            if is_new_user:
                await self._create_user_profile_for_oauth(response.user)
            
            # 创建用户响应对象
            user_response = UserResponse(
                id=response.user.id,
                email=response.user.email,
                full_name=response.user.user_metadata.get("full_name") if response.user.user_metadata else None,
                email_confirmed_at=response.user.email_confirmed_at,
                created_at=response.user.created_at,
                updated_at=response.user.updated_at
            )
            
            expires_at = int(datetime.now().timestamp()) + (response.session.expires_in or 3600)
            
            auth_response = AuthResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                expires_in=response.session.expires_in or 3600,
                expires_at=expires_at,
                user=user_response
            )
            
            # 添加is_new_user信息
            auth_response.is_new_user = is_new_user
            
            return auth_response
            
        except Exception as e:
            logger.error(f"OAuth会话交换失败: {e}")
            if "invalid_grant" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="授权码无效或已过期，请重新登录"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google登录失败，请稍后重试"
            )

    async def process_supabase_oauth(self, supabase_token: str, user_info: dict) -> AuthResponse:
        """
        处理Supabase OAuth token，直接使用Supabase session
        
        Args:
            supabase_token: Supabase会话的access_token
            user_info: Supabase用户信息
            
        Returns:
            AuthResponse: 包含Supabase session的认证响应
        """
        try:
            logger.info("🔄 开始处理Supabase OAuth token...")
            
            # 步骤1: 验证Supabase token并获取完整session信息
            try:
                # 使用Supabase token验证用户身份
                response = self.supabase.auth.get_user(supabase_token)
                if not response.user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="invalid_token"
                    )
                    
                supabase_user = response.user
                logger.info(f"✅ Supabase token verification successful: {supabase_user.email}")
                
                # 获取当前session信息（从Supabase）
                # 注意：我们需要从原始session中获取refresh_token等信息
                # 这里我们假设前端会传递完整的session信息
                
            except Exception as e:
                logger.error(f"❌ Supabase token verification failed: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="invalid_token"
                )
            
            # 步骤2: 检查用户是否已存在
            email = supabase_user.email
            user_id = supabase_user.id
            is_new_user = False
            
            try:
                # 检查用户档案是否存在
                profile_response = self.supabase.table('user_profiles').select("*").eq('user_id', user_id).execute()
                
                if not profile_response.data:
                    # 新用户，创建档案
                    logger.info(f"👤 Create new user profile: {email}")
                    await self._create_oauth_user_profile(supabase_user, user_info)
                    is_new_user = True
                else:
                    logger.info(f"👤 User already exists: {email}")
                    
            except Exception as e:
                logger.error(f"❌ User profile processing failed: {e}")
                logger.error(f"❌ Error type: {type(e).__name__}")
                logger.error(f"❌ Detailed error: {str(e)}")
                
                # 根据错误类型提供不同的处理策略
                error_str = str(e).lower()
                if '时序问题' in error_str or 'foreign key' in error_str:
                    error_detail = {
                        "error_type": "timing_issue",
                        "error_code": "user_creation_timing_error",
                        "message": "Timing issue occurred during user creation, please try logging in again later",
                        "retry_available": True,
                        "suggested_delay": 3000  # 建议等待3秒
                    }
                elif '重试' in error_str:
                    error_detail = {
                        "error_type": "retry_exhausted", 
                        "error_code": "profile_creation_retry_failed",
                        "message": "Profile creation retry failed, please try logging in again later",
                        "retry_available": True,
                        "suggested_delay": 10000  # 建议等待10秒
                    }
                else:
                    error_detail = {
                        "error_type": "profile_creation_failed",
                        "error_code": "unknown_profile_error",
                        "message": "Profile creation failed, please try again later",
                        "retry_available": True,
                        "suggested_delay": 5000  # 建议等待5秒
                    }
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail
                )
            
            # 步骤3: 直接使用Supabase session，不生成自定义JWT
            # 这样可以利用Supabase的内置refresh机制，避免短期过期问题
            logger.info(f"✅ Directly use Supabase session")
            
            # 构建用户响应
            user_response = UserResponse(
                id=supabase_user.id,
                email=supabase_user.email,
                full_name=supabase_user.user_metadata.get("full_name") if supabase_user.user_metadata else None,
                email_confirmed_at=supabase_user.email_confirmed_at,
                created_at=supabase_user.created_at,
                updated_at=supabase_user.updated_at
            )
            
            # 获取用户档案（用于响应）
            try:
                profile_response = self.supabase.table('user_profiles').select("*").eq('user_id', user_id).single().execute()
                user_profile = profile_response.data if profile_response.data else None
            except Exception as e:
                logger.warning(f"⚠️ Failed to get user profile: {e}")
                user_profile = None
            
            # 从user_info中获取session信息（前端应该传递完整的session）
            refresh_token = user_info.get('refresh_token', '')
            expires_in = user_info.get('expires_in', 3600)  # Supabase默认1小时
            expires_at = user_info.get('expires_at', int(datetime.now().timestamp()) + expires_in)
            
            auth_response = AuthResponse(
                access_token=supabase_token,  # 直接使用Supabase token
                refresh_token=refresh_token,
                expires_in=expires_in,
                expires_at=expires_at,
                user=user_response,
                is_new_user=is_new_user,
                message="Google login successful!" if not is_new_user else "Welcome to TextLingo2!"
            )
            
            logger.info(f"🎉 Supabase OAuth processing completed: {email}, new_user: {is_new_user}")
            return auth_response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"💥 Supabase OAuth处理失败: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="unknown_error"
            )

    async def _is_new_user(self, user_id: str) -> bool:
        """检查用户是否是新用户（是否已有用户档案）"""
        try:
            response = self.supabase.table('user_profiles').select("user_id").eq('user_id', user_id).execute()
            return len(response.data) == 0
        except Exception as e:
            logger.warning(f"检查新用户状态失败: {e}")
            return True  # 默认认为是新用户

    async def _create_user_profile_for_oauth(self, user) -> None:
        """为OAuth用户创建用户档案"""
        try:
            user_metadata = user.user_metadata if user.user_metadata else {}
            full_name = user_metadata.get('full_name', '') or user.email.split('@')[0]
            avatar_url = user_metadata.get('avatar_url')
            
            # 根据OAuth提供商设置默认语言，智能推断语言偏好
            provider = user_metadata.get('provider', 'google')
            locale = user_metadata.get('locale', 'en')
            
            native_language = 'en'  # OAuth用户默认英语
            if locale:
                if locale.startswith('zh'):
                    native_language = 'zh'
                elif locale.startswith('ja'):
                    native_language = 'ja'
                elif locale.startswith('ko'):
                    native_language = 'ko'
                elif locale.startswith('es'):
                    native_language = 'es'
                elif locale.startswith('fr'):
                    native_language = 'fr'
                elif locale.startswith('de'):
                    native_language = 'de'
            
            # 优先使用RPC函数创建档案，绕过RLS策略
            try:
                logger.info(f"🔄 Attempting to create OAuth user profile using RPC function: {user.email}")
                # 使用service role客户端确保有权限
                from app.services.supabase_client import supabase_service
                service_client = supabase_service.get_client()
                profile_response = service_client.rpc('create_user_profile_bypass_rls', {
                    'p_user_id': user.id,
                    'p_role': 'free',
                    'p_points': 350,
                    'p_native_language': native_language,
                    'p_full_name': full_name,
                    'p_learning_language': 'zh' if native_language != 'zh' else 'en',
                    'p_language_level': 'beginner',
                    'p_avatar_url': avatar_url,
                    'p_bio': None,
                    'p_profile_setup_completed': False  # Google用户需要确认设置
                }).execute()
                
                if profile_response.data:
                    logger.info(f"✅ OAuth user profile created successfully (RPC): {user.email}")
                    return
                else:
                    raise Exception("RPC call returned empty result")
                    
            except Exception as rpc_error:
                logger.warning(f"⚠️ RPC method failed, trying direct insert: {rpc_error}")
                
                # 回退到直接插入，添加缺失字段并使用service role
                profile_data = {
                    'user_id': user.id,
                    'email': user.email,  # 添加缺失字段
                    'full_name': full_name,
                    'avatar_url': avatar_url,
                    'bio': '',  # 添加缺失字段
                    'role': 'free',
                    'points': 350,  # 新用户赠送积分
                    'native_language': native_language,
                    'learning_language': 'zh' if native_language != 'zh' else 'en',
                    'language_level': 'beginner',
                    'profile_setup_completed': False  # Google用户需要确认设置
                }
                
                # 使用service role客户端进行插入
                service_client.table('user_profiles').insert(profile_data).execute()
                logger.info(f"✅ OAuth user profile created successfully (direct insert): {user.email}")
            
        except Exception as e:
            logger.error(f"❌ OAuth user profile creation failed: {e}")
            logger.error(f"❌ Detailed error: {str(e)}")
            
            # 检查具体错误类型，但不抛出异常让登录流程继续
            if 'not present in table "users"' in str(e):
                logger.error(f"❌ User ID {user.id} not present in auth.users table, possibly a timing issue")
            elif 'violates row-level security' in str(e):
                logger.error(f"❌ RLS policy prevents profile creation, database policy needs to be fixed")
            
            # 不抛出异常，让登录流程继续，用户可以稍后重试或手动创建档案
    
    async def _create_user_profile_with_token(self, supabase_user, google_user: dict, access_token: str) -> None:
        """使用JWT token创建用户档案（遵循RLS策略）"""
        try:
            logger.info(f"🔄 使用JWT token创建用户档案: {supabase_user.email}")
            
            # 从Google用户信息和Supabase用户信息中提取数据
            user_metadata = supabase_user.user_metadata if supabase_user.user_metadata else {}
            full_name = google_user.get('name', '') or user_metadata.get('full_name', '') or supabase_user.email.split('@')[0]
            avatar_url = google_user.get('picture') or user_metadata.get('avatar_url')
            locale = user_metadata.get('locale', 'zh')
            
            # 根据locale智能推断语言偏好
            native_language = 'en'  # 默认英语
            if locale:
                if locale.startswith('zh'):
                    native_language = 'zh'
                elif locale.startswith('ja'):
                    native_language = 'ja'
                elif locale.startswith('ko'):
                    native_language = 'ko'
                elif locale.startswith('es'):
                    native_language = 'es'
                elif locale.startswith('fr'):
                    native_language = 'fr'
                elif locale.startswith('de'):
                    native_language = 'de'
            
            # 使用用户客户端创建档案（遵循RLS策略）
            from app.services.supabase_client import supabase_service
            user_client = supabase_service.get_user_client(access_token)
            
            profile_data = {
                'user_id': supabase_user.id,
                'email': supabase_user.email,
                'full_name': full_name,
                'avatar_url': avatar_url,
                'bio': '',
                'role': 'free',
                'points': 350,  # 新用户赠送积分
                'native_language': native_language,
                'learning_language': 'zh' if native_language != 'zh' else 'en',
                'language_level': 'beginner',
                'profile_setup_completed': False  # Google用户需要确认设置
            }
            
            logger.info(f"🔄 插入用户档案数据: {profile_data}")
            response = user_client.table('user_profiles').insert(profile_data).execute()
            
            if response.data:
                logger.info(f"✅ 用户档案创建成功 (RLS遵循): {supabase_user.email}")
            else:
                raise Exception("插入用户档案返回空数据")
                
        except Exception as e:
            logger.error(f"❌ 使用token创建用户档案失败: {e}")
            logger.error(f"❌ 错误详情: {str(e)}")
            
            # 检查具体错误类型
            error_str = str(e).lower()
            if 'not present in table "users"' in error_str:
                logger.error(f"❌ 用户ID {supabase_user.id} 在auth.users表中不存在，可能是时序问题")
            elif 'violates row-level security' in error_str or 'rls' in error_str:
                logger.error(f"❌ RLS策略阻止了档案创建，需要检查数据库RLS策略")
            elif 'duplicate' in error_str or 'already exists' in error_str:
                logger.warning(f"⚠️ 用户档案已存在，跳过创建")
                return  # 不算错误
            
            raise  # 重新抛出异常让上层处理
    
    async def _create_mobile_user_profile(self, supabase_user, google_user: dict) -> None:
        """为移动端Google用户创建档案（使用重试机制，与web版本一致）"""
        try:
            full_name = google_user.get('name', '')
            avatar_url = google_user.get('picture')
            locale = google_user.get('locale', 'zh')
            
            # 根据locale设置默认语言
            native_language = 'zh'
            if locale:
                if locale.startswith('en'):
                    native_language = 'en'
                elif locale.startswith('ja'):
                    native_language = 'ja'
                elif locale.startswith('ko'):
                    native_language = 'ko'
            
            # 创建用户档案数据（移除email字段，user_profiles表中没有此字段）
            profile_data = {
                'user_id': supabase_user.id,
                'full_name': full_name,
                'avatar_url': avatar_url,
                'bio': '',
                'role': 'free',
                'points': 350,  # 新用户赠送积分
                'native_language': native_language,
                'learning_language': 'en' if native_language != 'en' else 'zh',
                'language_level': 'beginner',
                'profile_setup_completed': False  # Google用户需要确认设置
            }
            
            # 使用带重试机制的方法创建档案（与web版本保持一致）
            success = await self.create_user_profile_with_retry(
                supabase_user.id, 
                profile_data,
                max_retries=3
            )
            
            if success:
                logger.info(f"✅ 移动端用户档案创建成功: {supabase_user.email}")
            else:
                raise Exception("档案创建失败")
            
        except Exception as e:
            logger.error(f"❌ 移动端用户档案创建失败: {e}")
            raise

    async def _create_oauth_user_profile(self, supabase_user, user_info: dict) -> None:
        """为OAuth用户创建档案（增强版）"""
        try:
            # 从Supabase用户信息中提取数据
            user_metadata = supabase_user.user_metadata if supabase_user.user_metadata else {}
            
            # 从user_info中获取额外信息，参考cross-version-auth的逻辑
            # 用户名从邮箱前缀提取，如 a123@qq.com -> a123
            email_prefix = supabase_user.email.split('@')[0]
            full_name = (
                user_metadata.get('full_name') or 
                user_info.get('full_name') or 
                user_info.get('name') or
                email_prefix  # 使用邮箱前缀作为默认用户名
            )
            
            avatar_url = (
                user_metadata.get('avatar_url') or
                user_info.get('avatar_url') or
                user_info.get('picture')
            )
            
            # 智能推断语言偏好（基于浏览器语言和用户locale信息）
            locale = user_metadata.get('locale') or user_info.get('locale', 'zh')  # 默认中文
            native_language = 'zh'  # OAuth用户默认中文
            if locale:
                if locale.startswith('en'):
                    native_language = 'en'
                elif locale.startswith('ja'):
                    native_language = 'ja'
                elif locale.startswith('ko'):
                    native_language = 'ko'
                elif locale.startswith('es'):
                    native_language = 'es'
                elif locale.startswith('fr'):
                    native_language = 'fr'
                elif locale.startswith('de'):
                    native_language = 'de'
            
            # 使用增强的重试机制创建用户档案，添加缺失字段
            profile_data = {
                'user_id': supabase_user.id,
                'email': supabase_user.email,  # 添加缺失字段
                'full_name': full_name,
                'avatar_url': avatar_url,
                'bio': '',  # 添加缺失字段
                'role': 'free',
                'points': 350,  # 新用户赠送350积分
                'native_language': native_language,
                'learning_language': 'en' if native_language != 'en' else 'zh',
                'language_level': 'beginner',
                'profile_setup_completed': False  # Google用户需要确认设置
            }
            
            success = await self.create_user_profile_with_retry(supabase_user.id, profile_data)
            
            if not success:
                raise Exception("用户档案创建失败：重试次数已用完")
                
            logger.info(f"✅ OAuth用户档案创建成功: {supabase_user.email}")
            
        except Exception as e:
            logger.error(f"❌ OAuth用户档案创建失败ER04: {e}")
            logger.error(f"❌ 详细错误: {str(e)}")
            
            # 检查具体错误类型并提供更详细的错误信息
            error_str = str(e).lower()
            if 'not present in table "users"' in error_str or 'foreign key constraint' in error_str:
                logger.error(f"❌ 用户ID {supabase_user.id} 在auth.users表中不存在，时序问题")
                raise Exception(f"用户创建时序问题，请稍后重新登录: {str(e)}")
            elif 'violates row-level security' in error_str:
                logger.error(f"❌ RLS策略阻止档案创建")
                raise Exception(f"权限策略错误，请联系技术支持: {str(e)}")
            elif '重试次数已用完' in str(e):
                logger.error(f"❌ 重试机制用尽")
                raise Exception(f"档案创建重试失败，建议稍后重新登录: {str(e)}")
            else:
                logger.error(f"❌ 未分类的档案创建错误")
                raise Exception(f"档案创建失败，请稍后重试: {str(e)}")

    async def google_mobile_auth(self, access_token: str, id_token: Optional[str] = None) -> AuthResponse:
        """
        处理移动端Google Sign In - 使用Google ID token登录Supabase.
        这个逻辑现在模仿 supabase-oauth 流程.
        
        Args:
            access_token: Google access token (用于获取用户信息以创建档案).
            id_token: Google ID token (用于登录Supabase).
            
        Returns:
            AuthResponse: 认证响应, 包含Supabase的session.
        """
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google ID token is required for mobile sign-in."
            )

        try:
            logger.info("🔄 开始使用Google ID token进行Supabase登录...")
            
            # 使用Supabase的 sign_in_with_id_token, 这是处理OAuth的核心
            # 它会自动在Supabase Auth中创建或登录用户
            session_response = self.auth_client.sign_in_with_id_token({
                "provider": "google",
                "token": id_token,
            })

            if not session_response or not session_response.user or not session_response.session:
                raise AuthApiError("无法使用Google ID token登录Supabase", {})

            supabase_user = session_response.user
            supabase_session = session_response.session
            logger.info(f"✅ Supabase登录成功: {supabase_user.email}")

            # 检查用户是否在我们的系统中是“新”的 (即，是否有profile)
            from app.services.user_service import user_service
            user_profile = await user_service.get_user_profile(supabase_user.id)
            
            is_new_user = not user_profile

            if is_new_user:
                logger.info(f"📝 新用户，需要创建用户档案: {supabase_user.email}")
                # 为了填充档案，需要从Google获取一些额外信息
                import httpx
                async with httpx.AsyncClient() as client:
                    user_info_response = await client.get(
                        f"https://www.googleapis.com/oauth2/v2/userinfo?access_token={access_token}",
                    )
                    google_user_info = user_info_response.json() if user_info_response.status_code == 200 else {}
                
                try:
                    await self._create_mobile_user_profile(supabase_user, google_user_info)
                    logger.info(f"✅ 新用户档案创建成功: {supabase_user.email}")
                except Exception as profile_error:
                    logger.warning(f"⚠️ 用户档案创建失败，但登录继续: {profile_error}")
            else:
                 logger.info(f"✅ 找到现有用户档案: {supabase_user.email}")

            # 构建与 supabase-oauth 类似的 AuthResponse, 直接返回 Supabase 的 session
            user_response_model = UserResponse(
                id=supabase_user.id,
                email=supabase_user.email,
                full_name=supabase_user.user_metadata.get("full_name"),
                email_confirmed_at=supabase_user.email_confirmed_at,
                created_at=supabase_user.created_at,
                updated_at=supabase_user.updated_at
            )
            
            return AuthResponse(
                access_token=supabase_session.access_token,
                refresh_token=supabase_session.refresh_token,
                expires_in=supabase_session.expires_in,
                expires_at=supabase_session.expires_at,
                user=user_response_model,
                is_new_user=is_new_user,
                message="Google登录成功！" if not is_new_user else "欢迎使用TextLingo2！"
            )
            
        except AuthApiError as e:
            logger.error(f"Supabase Auth API 错误: {e.message}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google登录失败: {e.message}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"移动端Google登录未知错误: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Google登录失败，请稍后重试: {str(e)}"
            )


# 创建全局认证服务实例
auth_service = AuthService() 