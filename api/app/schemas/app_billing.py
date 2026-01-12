from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PeriodType(str, Enum):
    EARLY_USER = "EARLY_USER"
    TRIAL = "TRIAL"
    GRACE = "GRACE"


class AppBillingConfig(BaseModel):
    id: str
    config_key: str
    config_value: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserFreePeriod(BaseModel):
    id: str
    user_id: str
    period_type: PeriodType
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class UserFreePeriodCreate(BaseModel):
    user_id: str
    period_type: PeriodType
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None


class AppSubscriptionStatus(BaseModel):
    """用户App订阅状态响应"""
    user_id: str
    billing_enabled: bool = False
    has_premium_subscription: bool = False
    subscription_type: str = "FREE"  # FREE, PREMIUM, EARLY_USER, TRIAL, GRACE
    is_in_free_period: bool = False
    free_period_end: Optional[datetime] = None
    free_period_reason: Optional[str] = None
    available_features: List[str] = []
    restrictions: Dict[str, Any] = {}
    message: Optional[str] = None


class BillingConfigUpdate(BaseModel):
    """更新计费配置"""
    config_key: str
    config_value: str
    description: Optional[str] = None


class AppBillingStatsResponse(BaseModel):
    """App计费统计响应"""
    total_users: int
    premium_users: int
    free_period_users: int
    early_users: int
    trial_users: int
    grace_period_users: int
    billing_enabled: bool
    conversion_rate: float = 0.0