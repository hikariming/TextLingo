from typing import Optional, Dict, List, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, EmailStr


class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    native_language: Optional[str] = "zh"
    learning_language: Optional[str] = "en"
    language_level: Optional[str] = "beginner"
    interface_language: Optional[str] = "zh"  # 界面显示语言
    profile_setup_completed: Optional[bool] = False  # 是否完成初始设置


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    class Config:
        from_attributes = True


class UserProfile(UserProfileBase):
    id: str
    user_id: str
    email: str
    avatar_url: Optional[str] = None
    role: str
    points: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSubscriptionBase(BaseModel):
    plan_type: str = "free"
    plan_name: str = "Free Plan"
    status: str = "active"
    auto_renew: bool = False
    payment_method: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: str = "CNY"


class UserSubscriptionCreate(UserSubscriptionBase):
    end_date: Optional[datetime] = None


class UserSubscriptionUpdate(BaseModel):
    plan_type: Optional[str] = None
    plan_name: Optional[str] = None
    status: Optional[str] = None
    end_date: Optional[datetime] = None
    auto_renew: Optional[bool] = None


class UserSubscription(UserSubscriptionBase):
    id: str
    user_id: str
    start_date: datetime
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCompleteProfile(UserProfile):
    plan_type: Optional[str] = None
    plan_name: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_end_date: Optional[datetime] = None


class ProfileSetupRequest(BaseModel):
    """用户初始设置请求模型"""
    native_language: str
    learning_language: Optional[str] = "en"
    language_level: Optional[str] = "beginner"
    

class ProfileSetupResponse(BaseModel):
    """用户初始设置响应模型"""
    success: bool
    message: str
    profile: Optional[dict] = None


class AvatarUploadResponse(BaseModel):
    avatar_url: str
    message: str


# LingoCloud 统计相关 Schema
class ArticlesStats(BaseModel):
    """文章统计信息"""
    total_articles: int
    public_articles: int
    private_articles: int
    by_status: Dict[str, int]
    by_difficulty: Dict[str, int] 
    by_category: Dict[str, int]


class NovelsStats(BaseModel):
    """小说统计信息"""
    total_novels: int
    public_novels: int
    private_novels: int
    total_chapters: int
    by_language: Dict[str, int]


class ModelInfo(BaseModel):
    """AI模型信息"""
    id: str
    name: str
    provider: str
    description: str
    capabilities: List[str]
    required_tier: str
    points_per_1k_tokens: Optional[int] = None
    available: bool


class MembershipLimits(BaseModel):
    """会员限额信息"""
    plan_type: str
    plan_name: str
    limits: Dict[str, Any]  # 包含各种限额信息
    

class UserLingoCloudStats(BaseModel):
    """用户LingoCloud综合统计信息"""
    # 用户基本信息
    user_id: str
    email: str
    full_name: Optional[str] = None
    plan_type: str
    role: str
    points: int
    
    # 统计信息
    articles_stats: ArticlesStats
    novels_stats: NovelsStats
    
    # 可用模型
    available_models: List[ModelInfo]
    
    # 会员限额
    membership_limits: MembershipLimits
    
    # 使用情况对比限额
    usage_vs_limits: Dict[str, Any]


class LingoCloudStatsResponse(BaseModel):
    """LingoCloud统计响应"""
    success: bool
    message: str
    data: UserLingoCloudStats 