from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class UserRegisterRequest(BaseModel):
    """用户注册请求模型"""
    email: str
    password: str
    full_name: str  # 改为必填
    native_language: Optional[str] = "zh"  # 默认为中文

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('无效的电子邮件地址')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少为6位')
        return v
    
    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError('请输入昵称')
        if len(v.strip()) < 2:
            raise ValueError('昵称至少需要2个字符')
        return v.strip()
    
    @validator('native_language')
    def validate_native_language(cls, v):
        if v is not None:
            allowed_languages = ['zh', 'en', 'ja', 'ko', 'es', 'fr']
            if v not in allowed_languages:
                raise ValueError(f'讲解语言必须是以下之一: {allowed_languages}')
        return v


class UserLoginRequest(BaseModel):
    """用户登录请求模型"""
    email: str
    password: str
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('无效的电子邮件地址')
        return v


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: str
    email: str
    full_name: Optional[str] = None
    email_confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """认证响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int
    user: UserResponse
    is_new_user: Optional[bool] = False  # 是否是新用户
    message: Optional[str] = None  # 可选的消息字段，用于邮箱确认等提示


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT Token 载荷模型"""
    sub: Optional[str] = None  # subject (user id)
    exp: Optional[int] = None  # expiration time
    email: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """重置密码请求模型"""
    access_token: str  # 这里实际上是6位数字token
    new_password: str
    email: str
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少为6位')
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('无效的电子邮件地址')
        return v


class PasswordResetResponse(BaseModel):
    """重置密码响应模型"""
    success: bool
    message: str


class TokenLoginRequest(BaseModel):
    """跨版本token登录请求模型"""
    token: str


class TokenVerifyRequest(BaseModel):
    """token验证请求模型"""  
    token: str


class ForgotPasswordRequest(BaseModel):
    """忘记密码请求模型"""
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('无效的电子邮件地址')
        return v


class ForgotPasswordResponse(BaseModel):
    """忘记密码响应模型"""
    success: bool
    message: str


class GoogleOAuthRequest(BaseModel):
    """Google OAuth登录请求模型"""
    code: str  # Google OAuth授权码
    redirect_uri: Optional[str] = None  # 重定向URI，用于验证


class GoogleMobileAuthRequest(BaseModel):
    """Google移动端登录请求模型 - 使用access token而不是code"""
    access_token: str  # Google access token (from Google Sign In)
    id_token: Optional[str] = None  # Google ID token (optional)


class GoogleOAuthResponse(BaseModel):
    """Google OAuth登录响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int
    user: UserResponse
    user_profile: Optional[Dict[str, Any]] = None  # 用户档案信息
    is_new_user: bool = False  # 标识是否为新用户
    message: Optional[str] = None


class GoogleUserInfo(BaseModel):
    """Google用户信息模型"""
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    locale: Optional[str] = None 


class SupabaseOAuthRequest(BaseModel):
    """Supabase OAuth登录请求模型"""
    access_token: str  # Supabase会话的access_token
    user_info: Dict[str, Any]  # Supabase用户信息


class SupabaseOAuthResponse(BaseModel):
    """Supabase OAuth登录响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    expires_at: int
    user: UserResponse
    user_profile: Optional[Dict[str, Any]] = None
    is_new_user: bool = False
    message: Optional[str] = None


class OAuthErrorType(str, Enum):
    """OAuth错误类型"""
    INVALID_TOKEN = "invalid_token"
    EXPIRED_TOKEN = "expired_token"
    USER_CREATION_FAILED = "user_creation_failed"
    PROFILE_CREATION_FAILED = "profile_creation_failed"
    NETWORK_ERROR = "network_error"
    UNKNOWN_ERROR = "unknown_error"


class OAuthErrorResponse(BaseModel):
    """OAuth错误响应模型"""
    error_type: OAuthErrorType
    error_code: str
    message: str
    details: Optional[str] = None
    retry_available: bool = False 