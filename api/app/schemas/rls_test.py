from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class RlsTestDataBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="测试数据标题")
    content: Optional[str] = Field(None, description="测试数据内容")
    is_private: bool = Field(True, description="是否为私有数据")
    test_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="测试JSON数据")


class RlsTestDataCreate(RlsTestDataBase):
    """创建RLS测试数据的Schema"""
    pass


class RlsTestDataUpdate(BaseModel):
    """更新RLS测试数据的Schema"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="测试数据标题")
    content: Optional[str] = Field(None, description="测试数据内容")
    is_private: Optional[bool] = Field(None, description="是否为私有数据")
    test_data: Optional[Dict[str, Any]] = Field(None, description="测试JSON数据")


class RlsTestDataResponse(RlsTestDataBase):
    """RLS测试数据响应Schema"""
    id: int = Field(..., description="测试数据ID")
    user_id: uuid.UUID = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class RlsTestDataListResponse(BaseModel):
    """RLS测试数据列表响应Schema"""
    items: list[RlsTestDataResponse] = Field(..., description="测试数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页数量")
    has_next: bool = Field(..., description="是否有下一页")
    has_prev: bool = Field(..., description="是否有上一页")


class RlsTestStats(BaseModel):
    """RLS测试统计信息"""
    total_records: int = Field(..., description="总记录数")
    private_records: int = Field(..., description="私有记录数")
    public_records: int = Field(..., description="公共记录数")
    created_today: int = Field(..., description="今日创建数")
    user_id: uuid.UUID = Field(..., description="用户ID") 