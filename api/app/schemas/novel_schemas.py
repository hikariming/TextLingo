"""
小说相关的Pydantic数据模型
基于现有的material_schemas.py模式创建
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class NovelLanguage(str, Enum):
    """小说语言枚举"""
    JAPANESE = "ja"
    CHINESE = "zh"
    ENGLISH = "en"
    KOREAN = "ko"
    FRENCH = "fr"
    GERMAN = "de"
    SPANISH = "es"


class NovelStatus(str, Enum):
    """小说状态枚举"""
    DRAFT = "draft"          # 草稿状态
    PROCESSING = "processing"  # 处理中（上传/解析）
    ACTIVE = "active"        # 正常状态
    COMPLETED = "completed"   # 已完结
    ARCHIVED = "archived"    # 已归档


# ================================
# 小说主表相关模型
# ================================

class NovelBase(BaseModel):
    """小说基础模型"""
    title: str = Field(..., min_length=1, max_length=500, description="小说标题")
    author: Optional[str] = Field(None, max_length=200, description="小说作者")
    description: Optional[str] = Field(None, max_length=2000, description="小说描述/简介")
    language: NovelLanguage = Field(default=NovelLanguage.JAPANESE, description="小说主要语言")
    is_public: bool = Field(default=False, description="是否公开")
    cover_image_url: Optional[str] = Field(None, max_length=500, description="封面图片URL")
    original_filename: Optional[str] = Field(None, max_length=255, description="原始文件名")


class NovelCreate(NovelBase):
    """创建小说的模型"""
    pass


class NovelUpdate(BaseModel):
    """更新小说的模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=500, description="小说标题")
    author: Optional[str] = Field(None, max_length=200, description="小说作者")
    description: Optional[str] = Field(None, max_length=2000, description="小说描述/简介")
    language: Optional[NovelLanguage] = Field(None, description="小说主要语言")
    is_public: Optional[bool] = Field(None, description="是否公开")
    cover_image_url: Optional[str] = Field(None, max_length=500, description="封面图片URL")
    original_filename: Optional[str] = Field(None, max_length=255, description="原始文件名")


class NovelResponse(NovelBase):
    """小说响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="小说ID")
    user_id: str = Field(..., description="小说所有者用户ID")
    total_chapters: int = Field(default=0, description="总章节数")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class NovelListItem(BaseModel):
    """小说列表项模型（用于列表展示，数据较少）"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str = Field(..., description="小说ID")
    title: str = Field(..., description="小说标题")
    author: Optional[str] = Field(None, description="小说作者")
    language: NovelLanguage = Field(..., description="小说主要语言")
    is_public: bool = Field(..., description="是否公开")
    total_chapters: int = Field(default=0, description="总章节数")
    cover_image_url: Optional[str] = Field(None, description="封面图片URL")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class NovelListResponse(BaseModel):
    """小说列表响应模型"""
    novels: List[NovelListItem] = Field(default_factory=list, description="小说列表")
    total: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")


# ================================
# 公开小说相关模型（包含用户信息）
# ================================

class PublicNovelItem(NovelListItem):
    """公开小说列表项（包含用户信息）"""
    user_id: str = Field(..., description="小说所有者用户ID")


class PublicNovelListResponse(BaseModel):
    """公开小说列表响应模型"""
    novels: List[PublicNovelItem] = Field(default_factory=list, description="公开小说列表")
    total: int = Field(default=0, description="总数量")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")


# ================================
# 查询参数模型
# ================================

class NovelQueryParams(BaseModel):
    """小说查询参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="搜索关键词")
    language: Optional[NovelLanguage] = Field(None, description="筛选语言")
    is_public: Optional[bool] = Field(None, description="筛选公开状态")
    sort_by: str = Field(default="created_at", description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")


# ================================
# API响应包装模型
# ================================

class NovelCreateResponse(BaseModel):
    """创建小说响应"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="小说创建成功", description="响应消息")
    data: NovelResponse = Field(..., description="创建的小说数据")


class NovelUpdateResponse(BaseModel):
    """更新小说响应"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="小说更新成功", description="响应消息")
    data: NovelResponse = Field(..., description="更新的小说数据")


class NovelDeleteResponse(BaseModel):
    """删除小说响应"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="小说删除成功", description="响应消息")


# ================================
# 错误响应模型
# ================================

class NovelErrorResponse(BaseModel):
    """小说操作错误响应"""
    success: bool = Field(default=False, description="操作是否成功")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[dict] = Field(None, description="详细错误信息")


# ================================
# 批量操作模型
# ================================

class NovelBatchDeleteRequest(BaseModel):
    """批量删除小说请求"""
    novel_ids: List[str] = Field(..., min_items=1, max_items=50, description="要删除的小说ID列表")


class NovelBatchDeleteResponse(BaseModel):
    """批量删除小说响应"""
    success: bool = Field(default=True, description="操作是否成功")
    message: str = Field(default="批量删除成功", description="响应消息")
    deleted_count: int = Field(..., description="成功删除的数量")
    failed_ids: List[str] = Field(default_factory=list, description="删除失败的小说ID列表")


# ================================
# 统计信息模型
# ================================

class NovelStats(BaseModel):
    """小说统计信息"""
    total_novels: int = Field(default=0, description="总小说数")
    public_novels: int = Field(default=0, description="公开小说数")
    private_novels: int = Field(default=0, description="私有小说数")
    total_chapters: int = Field(default=0, description="总章节数")
    by_language: dict = Field(default_factory=dict, description="按语言分组统计")


class NovelStatsResponse(BaseModel):
    """小说统计响应"""
    success: bool = Field(default=True, description="操作是否成功")
    data: NovelStats = Field(..., description="统计数据")