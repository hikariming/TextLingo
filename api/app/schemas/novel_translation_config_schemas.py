"""
小说用户翻译配置相关的Pydantic数据模型
存储用户对每本小说的个性化翻译和阅读设置
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TranslationMode(str, Enum):
    """翻译模式枚举"""
    COMPARISON = "comparison"  # 对比模式：原文和译文并排显示
    MIXED = "mixed"           # 混合模式：根据比例随机显示原文或译文
    TIPS = "tips"             # 提示模式：仅显示原文，悬停显示译文


class FontFamily(str, Enum):
    """字体系列枚举"""
    SYSTEM = "system"         # 系统字体
    SERIF = "serif"          # 衬线字体
    MONO = "mono"            # 等宽字体
    NOTO_SANS = "noto-sans"  # Noto Sans
    SOURCE_HAN = "source-han" # 思源黑体
    PINGFANG = "pingfang"     # 苹方字体


# ================================
# 翻译配置基础模型
# ================================

class NovelTranslationConfigBase(BaseModel):
    """小说翻译配置基础模型"""
    is_translation_enabled: bool = Field(default=False, description="是否启用翻译功能")
    source_language: str = Field(default="English", max_length=50, description="源语言")
    target_language: str = Field(default="Chinese", max_length=50, description="目标语言")
    custom_source_language: Optional[str] = Field(None, max_length=100, description="自定义源语言")
    custom_target_language: Optional[str] = Field(None, max_length=100, description="自定义目标语言")
    translation_mode: TranslationMode = Field(default=TranslationMode.COMPARISON, description="翻译模式")
    mixed_ratio: int = Field(default=30, ge=0, le=100, description="混合模式下的翻译比例(0-100%)")
    mixed_seed: int = Field(default=0, description="混合模式的随机种子")
    font_size: int = Field(default=16, ge=12, le=24, description="字体大小(12-24px)")
    font_family: FontFamily = Field(default=FontFamily.SYSTEM, description="字体系列")
    is_ai_visible: bool = Field(default=False, description="AI助手面板是否可见")


class NovelTranslationConfigCreate(NovelTranslationConfigBase):
    """创建翻译配置请求模型"""
    novel_id: str = Field(..., description="小说ID")


class NovelTranslationConfigUpdate(BaseModel):
    """更新翻译配置请求模型 - 所有字段都是可选的"""
    is_translation_enabled: Optional[bool] = Field(None, description="是否启用翻译功能")
    source_language: Optional[str] = Field(None, max_length=50, description="源语言")
    target_language: Optional[str] = Field(None, max_length=50, description="目标语言")
    custom_source_language: Optional[str] = Field(None, max_length=100, description="自定义源语言")
    custom_target_language: Optional[str] = Field(None, max_length=100, description="自定义目标语言")
    translation_mode: Optional[TranslationMode] = Field(None, description="翻译模式")
    mixed_ratio: Optional[int] = Field(None, ge=0, le=100, description="混合模式下的翻译比例(0-100%)")
    mixed_seed: Optional[int] = Field(None, description="混合模式的随机种子")
    font_size: Optional[int] = Field(None, ge=12, le=24, description="字体大小(12-24px)")
    font_family: Optional[FontFamily] = Field(None, description="字体系列")
    is_ai_visible: Optional[bool] = Field(None, description="AI助手面板是否可见")


class NovelTranslationConfigResponse(NovelTranslationConfigBase):
    """翻译配置响应模型"""
    id: str = Field(..., description="配置ID")
    user_id: str = Field(..., description="用户ID")
    novel_id: str = Field(..., description="小说ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    last_used_at: datetime = Field(..., description="最后使用时间")
    
    model_config = ConfigDict(from_attributes=True)


# ================================
# API响应模型
# ================================

class NovelTranslationConfigCreateResponse(BaseModel):
    """创建翻译配置响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: NovelTranslationConfigResponse = Field(..., description="翻译配置数据")


class NovelTranslationConfigUpdateResponse(BaseModel):
    """更新翻译配置响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: NovelTranslationConfigResponse = Field(..., description="更新后的翻译配置数据")


class NovelTranslationConfigGetResponse(BaseModel):
    """获取翻译配置响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[NovelTranslationConfigResponse] = Field(None, description="翻译配置数据，如果没有配置则为None")


class NovelTranslationConfigListResponse(BaseModel):
    """批量获取翻译配置响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: List[NovelTranslationConfigResponse] = Field(..., description="翻译配置列表")
    total: int = Field(..., description="总配置数量")


class NovelTranslationConfigDeleteResponse(BaseModel):
    """删除翻译配置响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")


# ================================
# 批量操作模型
# ================================

class NovelTranslationConfigBatchRequest(BaseModel):
    """批量获取翻译配置请求"""
    novel_ids: List[str] = Field(..., description="小说ID列表", max_items=50)


class NovelTranslationConfigBatchResponse(BaseModel):
    """批量获取翻译配置响应"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="响应消息")
    data: dict[str, Optional[NovelTranslationConfigResponse]] = Field(
        ..., 
        description="翻译配置映射，key为novel_id，value为配置数据（如果没有配置则为None）"
    )