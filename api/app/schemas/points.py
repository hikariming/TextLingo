from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class TransactionType(str, Enum):
    """交易类型枚举"""
    CONSUME = "consume"
    RECHARGE = "recharge"
    REWARD = "reward"
    REFUND = "refund"


class ServiceType(str, Enum):
    """服务类型枚举"""
    AI_CHAT = "ai_chat"
    AI_TRANSLATION = "ai_translation"
    AI_ANALYSIS = "ai_analysis"
    AI_GENERATION = "ai_generation"
    PREMIUM_FEATURE = "premium_feature"
    DIFY_CHAT = "dify_chat"
    VOICE_SYNTHESIS = "voice_synthesis"


class TransactionStatus(str, Enum):
    """交易状态枚举"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class BillingType(str, Enum):
    """计费类型枚举"""
    PER_REQUEST = "per_request"
    PER_TOKEN = "per_token"
    PER_CHARACTER = "per_character"


# 积分交易基础模型
class PointTransactionBase(BaseModel):
    transaction_type: TransactionType = TransactionType.CONSUME
    points_change: int
    service_type: Optional[ServiceType] = None
    aimodel_name: Optional[str] = None
    tokens_used: Optional[int] = 0
    description: Optional[str] = None
    request_id: Optional[str] = None
    service_details: Optional[Dict[str, Any]] = None


# 创建积分交易
class PointTransactionCreate(PointTransactionBase):
    pass


# 积分交易响应模型
class PointTransaction(PointTransactionBase):
    id: str
    user_id: str
    points_before: int
    points_after: int
    status: TransactionStatus = TransactionStatus.COMPLETED
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 积分消费请求
class ConsumePointsRequest(BaseModel):
    service_type: ServiceType
    aimodel_name: Optional[str] = None
    tokens_used: Optional[int] = 0
    description: Optional[str] = None
    request_id: Optional[str] = None
    service_details: Optional[Dict[str, Any]] = None


# 积分充值请求
class RechargePointsRequest(BaseModel):
    points_to_add: int = Field(..., gt=0, description="充值积分数，必须大于0")
    description: Optional[str] = "积分充值"
    request_id: Optional[str] = None


# 积分消费响应
class ConsumePointsResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    points_before: Optional[int] = None
    points_after: Optional[int] = None
    points_consumed: Optional[int] = None
    error: Optional[str] = None
    message: Optional[str] = None
    current_points: Optional[int] = None
    required_points: Optional[int] = None


# 积分充值响应
class RechargePointsResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    points_before: Optional[int] = None
    points_after: Optional[int] = None
    points_added: Optional[int] = None


# 用户积分余额
class UserPointsBalance(BaseModel):
    user_id: str
    email: str
    total_points: int
    total_consumed: int
    total_recharged: int
    total_rewarded: int
    total_transactions: int


# 积分价格配置基础模型
class PointPricingConfigBase(BaseModel):
    service_type: ServiceType
    aimodel_name: str
    billing_type: BillingType = BillingType.PER_REQUEST
    points_per_unit: int = Field(..., gt=0, description="每单位消耗的积分数")
    unit_description: Optional[str] = None
    is_active: bool = True


# 创建价格配置
class PointPricingConfigCreate(PointPricingConfigBase):
    pass


# 更新价格配置
class PointPricingConfigUpdate(BaseModel):
    billing_type: Optional[BillingType] = None
    points_per_unit: Optional[int] = Field(None, gt=0)
    unit_description: Optional[str] = None
    is_active: Optional[bool] = None


# 价格配置响应模型
class PointPricingConfig(PointPricingConfigBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 积分消费计算请求
class CalculatePointsRequest(BaseModel):
    service_type: ServiceType
    aimodel_name: Optional[str] = None
    tokens_used: Optional[int] = 0
    characters_count: Optional[int] = 0


# 积分消费计算响应
class CalculatePointsResponse(BaseModel):
    points_required: int
    billing_type: BillingType
    unit_description: str
    service_type: ServiceType
    aimodel_name: str


# 积分历史查询
class PointTransactionQuery(BaseModel):
    transaction_type: Optional[TransactionType] = None
    service_type: Optional[ServiceType] = None
    status: Optional[TransactionStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


# 分页响应
class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


# 积分交易历史响应
class PointTransactionHistoryResponse(PaginatedResponse):
    items: list[PointTransaction]