"""
小说分段相关的Pydantic模式定义
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SegmentationMode(str, Enum):
    """分段模式枚举"""
    REGEX = "regex"            # 正则表达式分段
    SEMANTIC = "semantic"      # 语义分段（根据内置规则）
    PARAGRAPH = "paragraph"    # 段落分段
    SENTENCE = "sentence"      # 句子分段
    CHARACTER = "character"    # 字符数分段
    AUTO_SIMPLE = "auto_simple"  # 自动简单分段（10000字符+换行符优化）


class SegmentationConfigRequest(BaseModel):
    """分段配置请求"""
    primary_segmentation_mode: SegmentationMode = Field(
        SegmentationMode.SEMANTIC, 
        description="主分段模式，用于章节级切分"
    )
    secondary_segmentation_mode: Optional[SegmentationMode] = Field(
        SegmentationMode.PARAGRAPH,
        description="次级分段模式，当主分段字数超限时使用"
    )
    
    max_chars_per_segment: int = Field(
        30000, 
        ge=500, 
        le=100000, 
        description="每个最终分段的最大允许字符数"
    )
    
    language: str = Field(
        "zh", 
        description="内容语言，用于语义分段"
    )
    
    # REGEX 模式配置
    custom_regex_separators: Optional[List[str]] = Field(
        None, 
        description="用于章节切分的自定义正则表达式列表"
    )
    
    # CHARACTER 模式配置
    characters_per_segment: int = Field(
        2000, 
        ge=100, 
        le=10000, 
        description="在 'character' 模式下，每个分段的目标字符数"
    )

    # PARAGRAPH 模式配置
    paragraphs_per_segment: int = Field(
        10, 
        ge=1, 
        le=100, 
        description="在 'paragraph' 模式下，每个分段的目标段落数"
    )
    
    # SENTENCE 模式配置
    sentences_per_segment: int = Field(
        20, 
        ge=1, 
        le=200, 
        description="在 'sentence' 模式下，每个分段的目标句子数"
    )


class SegmentInfo(BaseModel):
    """分段信息"""
    id: str = Field(..., description="分段ID")
    title: str = Field(..., description="分段标题")
    content: str = Field(..., description="分段内容")
    order: int = Field(..., description="分段顺序")
    char_count: int = Field(..., description="字符数")
    paragraph_count: int = Field(..., description="段落数")
    sentence_count: int = Field(..., description="句子数")


class SegmentationPreviewRequest(BaseModel):
    """分段预览请求"""
    novel_id: str = Field(..., description="小说ID")
    config: SegmentationConfigRequest = Field(..., description="分段配置")
    max_segments: Optional[int] = Field(5, ge=1, le=10, description="预览段数")


class SegmentationPreviewResponse(BaseModel):
    """分段预览响应"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("分段预览成功", description="响应消息")
    data: Dict[str, Any] = Field(..., description="预览数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "分段预览成功",
                "data": {
                    "total_segments": 15,
                    "preview_segments": [
                        "第一段内容预览...",
                        "第二段内容预览...",
                        "第三段内容预览..."
                    ],
                    "warnings": [
                        "第二章因内容过长（45000字）已被自动切分为3个部分。"
                    ],
                    "config": {
                        "primary_segmentation_mode": "regex",
                        "max_chars_per_segment": 30000,
                        "language": "zh",
                        "custom_regex_separators": ["^第[一二三四五六七八九十百]+章.*"]
                    }
                }
            }
        }


class SegmentationRequest(BaseModel):
    """分段处理请求"""
    novel_id: str = Field(..., description="小说ID")
    config: SegmentationConfigRequest = Field(..., description="分段配置")


class SegmentationResponse(BaseModel):
    """分段处理响应"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("分段处理成功", description="响应消息")
    data: Dict[str, Any] = Field(..., description="分段结果")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "分段处理成功",
                "data": {
                    "novel_id": "123e4567-e89b-12d3-a456-426614174000",
                    "total_segments": 15,
                    "total_chapters": 15,
                    "processing_time": 2.5,
                    "config": {
                        "mode": "semantic",
                        "language": "ja"
                    }
                }
            }
        }


class SegmentationStatsResponse(BaseModel):
    """分段统计响应"""
    success: bool = Field(True, description="是否成功")
    message: str = Field("获取统计信息成功", description="响应消息")
    data: Dict[str, Any] = Field(..., description="统计数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "获取统计信息成功",
                "data": {
                    "novel_id": "123e4567-e89b-12d3-a456-426614174000",
                    "total_chapters": 15,
                    "total_characters": 45000,
                    "average_chapter_length": 3000,
                    "shortest_chapter": 1500,
                    "longest_chapter": 4500,
                    "segmentation_config": {
                        "mode": "semantic",
                        "language": "ja"
                    }
                }
            }
        } 