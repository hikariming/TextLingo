"""
小说阅读进度相关的数据结构和API模式
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


# ================================
# 基础数据模型
# ================================

class NovelProgress(BaseModel):
    """小说阅读进度基础模型"""
    id: UUID
    user_id: UUID
    novel_id: UUID
    last_read_chapter_id: Optional[UUID] = None
    last_read_segment_id: Optional[str] = None
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    last_read_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ================================
# 请求数据模型
# ================================

class UpdateProgressRequest(BaseModel):
    """更新阅读进度请求"""
    last_read_chapter_id: Optional[UUID] = Field(None, description="最后阅读的章节ID")
    last_read_segment_id: Optional[str] = Field(None, description="最后阅读的段落/片段ID")
    progress_percentage: float = Field(ge=0.0, le=100.0, description="阅读进度百分比")

    class Config:
        json_schema_extra = {
            "example": {
                "last_read_chapter_id": "123e4567-e89b-12d3-a456-426614174000",
                "last_read_segment_id": "seg-003",
                "progress_percentage": 25.5
            }
        }


class BatchUpdateProgressRequest(BaseModel):
    """批量更新阅读进度请求"""
    progress_updates: list[UpdateProgressRequest] = Field(..., description="进度更新列表")

    class Config:
        json_schema_extra = {
            "example": {
                "progress_updates": [
                    {
                        "novel_id": "123e4567-e89b-12d3-a456-426614174000",
                        "last_read_segment_id": "seg-005",
                        "progress_percentage": 30.0
                    }
                ]
            }
        }


# ================================
# 响应数据模型
# ================================

class NovelProgressResponse(BaseModel):
    """小说阅读进度响应"""
    id: UUID
    user_id: UUID
    novel_id: UUID
    last_read_chapter_id: Optional[UUID] = None
    last_read_segment_id: Optional[str] = None
    progress_percentage: float
    last_read_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UpdateProgressResponse(BaseModel):
    """更新阅读进度响应"""
    success: bool
    message: str
    data: NovelProgressResponse

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "阅读进度更新成功",
                "data": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "user-uuid",
                    "novel_id": "novel-uuid",
                    "last_read_segment_id": "seg-005",
                    "progress_percentage": 30.0,
                    "last_read_at": "2024-01-15T10:30:00Z",
                    "created_at": "2024-01-15T09:00:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            }
        }


class GetProgressResponse(BaseModel):
    """获取阅读进度响应"""
    success: bool
    message: str
    data: Optional[NovelProgressResponse] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "获取阅读进度成功",
                "data": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "user-uuid",
                    "novel_id": "novel-uuid",
                    "last_read_segment_id": "seg-003",
                    "progress_percentage": 25.5,
                    "last_read_at": "2024-01-15T10:30:00Z",
                    "created_at": "2024-01-15T09:00:00Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            }
        }


class UserNovelProgressListResponse(BaseModel):
    """用户所有小说阅读进度列表响应"""
    success: bool
    message: str
    data: list[NovelProgressResponse]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "获取阅读进度列表成功",
                "data": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "user-uuid",
                        "novel_id": "novel-uuid-1",
                        "last_read_segment_id": "seg-003",
                        "progress_percentage": 25.5,
                        "last_read_at": "2024-01-15T10:30:00Z",
                        "created_at": "2024-01-15T09:00:00Z",
                        "updated_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "total": 1
            }
        }


# ================================
# 扩展数据模型（包含小说信息）
# ================================

class NovelProgressWithInfo(BaseModel):
    """包含小说信息的阅读进度"""
    id: UUID
    user_id: UUID
    novel_id: UUID
    last_read_chapter_id: Optional[UUID] = None
    last_read_segment_id: Optional[str] = None
    progress_percentage: float
    last_read_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # 小说基本信息
    novel_title: str
    novel_author: Optional[str] = None
    novel_cover_image_url: Optional[str] = None
    novel_language: str
    novel_total_chapters: int

    class Config:
        from_attributes = True


class UserNovelProgressWithInfoResponse(BaseModel):
    """用户所有小说阅读进度（包含小说信息）列表响应"""
    success: bool
    message: str
    data: list[NovelProgressWithInfo]
    total: int

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "获取阅读进度列表成功",
                "data": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "user-uuid",
                        "novel_id": "novel-uuid-1",
                        "last_read_segment_id": "seg-003",
                        "progress_percentage": 25.5,
                        "last_read_at": "2024-01-15T10:30:00Z",
                        "created_at": "2024-01-15T09:00:00Z",
                        "updated_at": "2024-01-15T10:30:00Z",
                        "novel_title": "测试小说",
                        "novel_author": "测试作者",
                        "novel_language": "ja",
                        "novel_total_chapters": 10
                    }
                ],
                "total": 1
            }
        }


# ================================
# 统计数据模型
# ================================

class ReadingStats(BaseModel):
    """阅读统计信息"""
    total_novels: int = Field(description="总小说数")
    novels_in_progress: int = Field(description="正在阅读的小说数")
    novels_completed: int = Field(description="已完成的小说数")
    total_reading_time_minutes: int = Field(description="总阅读时间（分钟）")
    average_progress: float = Field(description="平均阅读进度")
    last_read_novel_id: Optional[UUID] = Field(None, description="最近阅读的小说ID")
    last_read_at: Optional[datetime] = Field(None, description="最近阅读时间")

    class Config:
        json_schema_extra = {
            "example": {
                "total_novels": 5,
                "novels_in_progress": 3,
                "novels_completed": 2,
                "total_reading_time_minutes": 1200,
                "average_progress": 45.5,
                "last_read_novel_id": "123e4567-e89b-12d3-a456-426614174000",
                "last_read_at": "2024-01-15T10:30:00Z"
            }
        }


class ReadingStatsResponse(BaseModel):
    """阅读统计响应"""
    success: bool
    message: str
    data: ReadingStats

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "获取阅读统计成功",
                "data": {
                    "total_novels": 5,
                    "novels_in_progress": 3,
                    "novels_completed": 2,
                    "total_reading_time_minutes": 1200,
                    "average_progress": 45.5,
                    "last_read_novel_id": "123e4567-e89b-12d3-a456-426614174000",
                    "last_read_at": "2024-01-15T10:30:00Z"
                }
            }
        } 