"""
小说管理API端点
基于现有的material endpoint模式实现，支持RLS鉴权
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Header, Body, UploadFile, File
from typing import List, Optional
from app.services.novel_service import NovelService
from app.schemas.novel_schemas import (
    NovelCreate, NovelUpdate, NovelResponse, NovelListResponse,
    PublicNovelListResponse, NovelQueryParams, NovelStats,
    NovelCreateResponse, NovelUpdateResponse, NovelDeleteResponse,
    NovelBatchDeleteRequest, NovelBatchDeleteResponse, NovelStatsResponse
)
from app.schemas.novel_segmentation_schemas import (
    SegmentationPreviewRequest, SegmentationPreviewResponse,
    SegmentationRequest, SegmentationResponse,
    SegmentationStatsResponse
)
from app.schemas.novel_progress_schemas import (
    UpdateProgressRequest, UpdateProgressResponse, GetProgressResponse,
    UserNovelProgressListResponse, UserNovelProgressWithInfoResponse,
    ReadingStatsResponse
)
from app.schemas.auth import UserResponse
from app.core.dependencies import get_current_user, get_current_user_with_token, get_language
from app.core.i18n import SupportedLanguage, get_message, get_localized_status_text
import structlog

logger = structlog.get_logger()

router = APIRouter()

# 初始化服务
novel_service = NovelService()


# ================================
# 小说CRUD操作
# ================================

@router.post("/", response_model=NovelCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_novel(
    novel_data: NovelCreate,
    user_info = Depends(get_current_user_with_token),
    language: SupportedLanguage = Depends(get_language)
):
    """创建小说"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Creating novel", user_id=user_id, title=novel_data.title)
        
        novel = await novel_service.create_novel(user_id, novel_data, access_token)
        
        return NovelCreateResponse(
            success=True,
            message=get_message("novel_created_success", language),
            data=novel
        )
        
    except Exception as e:
        logger.error(f"Error creating novel: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("novel_creation_failed", language, error=str(e))
        )

# ================================
# 小说文件上传
# ================================

@router.post("/{novel_id}/upload", status_code=status.HTTP_200_OK)
async def upload_novel_file(
    novel_id: str = Path(..., description="小说ID"),
    file: UploadFile = File(..., description="小说文件"),
    user_info = Depends(get_current_user_with_token),
    language: SupportedLanguage = Depends(get_language)
):
    """上传小说文件到存储桶"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Uploading novel file", user_id=user_id, novel_id=novel_id, filename=file.filename)
        
        # 验证文件类型
        supported_types = ['text/plain', 'application/epub+zip']
        if file.content_type not in supported_types:
            # 对于EPUB文件，某些浏览器可能发送不同的content-type
            if not (file.filename and file.filename.lower().endswith('.epub')):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=get_message("supported_formats_error", language)
                )
        
        # 验证文件大小 (50MB限制)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_message("file_size_exceeded", language)
            )
        
        if len(file_content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_message("file_empty", language)
            )
        
        # 上传文件
        storage_path = await novel_service.upload_novel_file(
            user_id=user_id,
            novel_id=novel_id,
            file_content=file_content,
            access_token=access_token,
            filename=file.filename
        )
        
        return {
            "success": True,
            "message": get_message("file_upload_success", language),
            "storage_path": storage_path,
            "file_size": len(file_content)
        }
        
    except ValueError as ve:
        logger.warning(f"Validation error uploading novel file: {ve}", user_id=current_user.id, novel_id=novel_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Error uploading novel file: {e}", user_id=current_user.id, novel_id=novel_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("file_upload_failed", language, error=str(e))
        )

# ================================
# 其他小说操作
# ================================

@router.get("/", response_model=NovelListResponse)
async def list_user_novels(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    filter_language: Optional[str] = Query(None, alias="language", description="筛选语言"),
    is_public: Optional[bool] = Query(None, description="筛选公开状态"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向"),
    user_info = Depends(get_current_user_with_token),
    language: SupportedLanguage = Depends(get_language)
):
    """获取用户小说列表"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        # 构建查询参数
        query = NovelQueryParams(
            page=page,
            page_size=page_size,
            search=search,
            language=filter_language,
            is_public=is_public,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info("Listing user novels", user_id=user_id, page=page)
        
        novels_response = await novel_service.list_user_novels(user_id, query, access_token)
        
        return novels_response
        
    except Exception as e:
        logger.error(f"Error listing user novels: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("novel_list_failed", language, error=str(e))
        )


@router.get("/public", response_model=PublicNovelListResponse)
async def list_public_novels(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    language: Optional[str] = Query(None, description="筛选语言"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="排序方向")
):
    """获取公开小说列表（无需登录）"""
    try:
        # 构建查询参数
        query = NovelQueryParams(
            page=page,
            page_size=page_size,
            search=search,
            language=language,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        logger.info("Listing public novels", page=page)
        
        novels_response = await novel_service.list_public_novels(query)
        
        return novels_response
        
    except Exception as e:
        logger.error(f"Error listing public novels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取公开小说列表失败: {str(e)}"
        )


@router.get("/{novel_id}", response_model=NovelResponse)
async def get_novel(
    novel_id: str = Path(..., description="小说ID"),
    user_info = Depends(get_current_user_with_token),
    language: SupportedLanguage = Depends(get_language)
):
    """获取单个小说详情"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting novel", novel_id=novel_id, user_id=user_id)
        
        novel = await novel_service.get_novel(novel_id, user_id, access_token)
        
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message("novel_not_found", language)
            )
        
        return novel
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting novel: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("novel_details_failed", language, error=str(e))
        )


@router.put("/{novel_id}", response_model=NovelUpdateResponse)
async def update_novel(
    novel_id: str = Path(..., description="小说ID"),
    novel_data: NovelUpdate = ...,
    user_info = Depends(get_current_user_with_token)
):
    """更新小说信息"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Updating novel", novel_id=novel_id, user_id=user_id)
        
        novel = await novel_service.update_novel(novel_id, user_id, novel_data, access_token)
        
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="小说不存在或您无权修改"
            )
        
        return NovelUpdateResponse(
            success=True,
            message="小说更新成功",
            data=novel
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating novel: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新小说失败: {str(e)}"
        )


@router.delete("/{novel_id}", response_model=NovelDeleteResponse)
async def delete_novel(
    novel_id: str = Path(..., description="小说ID"),
    user_info = Depends(get_current_user_with_token)
):
    """删除小说"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Deleting novel", novel_id=novel_id, user_id=user_id)
        
        success = await novel_service.delete_novel(novel_id, user_id, access_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="小说不存在或您无权删除"
            )
        
        return NovelDeleteResponse(
            success=True,
            message="小说删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting novel: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除小说失败: {str(e)}"
        )





# ================================
# 批量操作
# ================================

@router.post("/batch/delete", response_model=NovelBatchDeleteResponse)
async def batch_delete_novels(
    request: NovelBatchDeleteRequest,
    user_info = Depends(get_current_user_with_token)
):
    """批量删除小说"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Batch deleting novels", user_id=user_id, count=len(request.novel_ids))
        
        deleted_count, failed_ids = await novel_service.batch_delete_novels(
            user_id, request.novel_ids, access_token
        )
        
        return NovelBatchDeleteResponse(
            success=True,
            message=f"成功删除{deleted_count}部小说",
            deleted_count=deleted_count,
            failed_ids=failed_ids
        )
        
    except Exception as e:
        logger.error(f"Error batch deleting novels: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除小说失败: {str(e)}"
        )


# ================================
# 小说状态操作
# ================================

@router.patch("/{novel_id}/toggle-public", response_model=NovelUpdateResponse)
async def toggle_novel_public_status(
    novel_id: str = Path(..., description="小说ID"),
    is_public: bool = Query(..., description="是否公开"),
    user_info = Depends(get_current_user_with_token),
    language: SupportedLanguage = Depends(get_language)
):
    """切换小说公开状态"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Toggling novel public status", novel_id=novel_id, user_id=user_id, is_public=is_public)
        
        novel = await novel_service.toggle_novel_public_status(
            novel_id, user_id, is_public, access_token
        )
        
        if not novel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=get_message("novel_not_found", language)
            )
        
        status_text = get_localized_status_text(is_public, language)
        return NovelUpdateResponse(
            success=True,
            message=get_message("public_status_updated", language, status=status_text),
            data=novel
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling novel public status: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_message("public_status_update_failed", language, error=str(e))
        )


# ================================
# 统计信息
# ================================

@router.get("/stats/user", response_model=NovelStatsResponse)
async def get_user_novel_stats(
    user_info = Depends(get_current_user_with_token)
):
    """获取用户小说统计信息"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting user novel stats", user_id=user_id)
        
        stats = await novel_service.get_user_novel_stats(user_id, access_token)
        
        return NovelStatsResponse(
            success=True,
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting user novel stats: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


# ================================
# 系统管理接口（内部使用）
# ================================

@router.patch("/{novel_id}/chapter-count", include_in_schema=False)
async def update_novel_chapter_count(
    novel_id: str = Path(..., description="小说ID"),
    chapter_count: int = Query(..., description="章节数量"),
    authorization: Optional[str] = Header(None)
):
    """更新小说章节数（系统级接口）"""
    try:
        # 简单的内部API验证（在实际生产中应使用更安全的验证方式）
        if not authorization or not authorization.startswith("Bearer system-"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="系统级接口需要特殊授权"
            )
        
        logger.info("Updating novel chapter count (system)", novel_id=novel_id, chapter_count=chapter_count)
        
        success = await novel_service.update_novel_chapter_count(novel_id, chapter_count)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="小说不存在"
            )
        
        return {"success": True, "message": "章节数更新成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating novel chapter count: {e}", novel_id=novel_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新章节数失败: {str(e)}"
        )


# ================================
# 辅助接口
# ================================

@router.get("/{novel_id}/ownership", include_in_schema=False)
async def check_novel_ownership(
    novel_id: str = Path(..., description="小说ID"),
    current_user: UserResponse = Depends(get_current_user)
):
    """检查小说所有权（内部使用）"""
    try:
        user_id = current_user.id
        
        is_owner = await novel_service.check_novel_ownership(novel_id, user_id)
        
        return {
            "novel_id": novel_id,
            "user_id": user_id,
            "is_owner": is_owner
        }
        
    except Exception as e:
        logger.error(f"Error checking novel ownership: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"检查所有权失败: {str(e)}"
        )


# ================================
# 小说分段相关接口
# ================================

@router.post("/{novel_id}/segmentation/preview", response_model=SegmentationPreviewResponse)
async def preview_novel_segmentation(
    novel_id: str = Path(..., description="小说ID"),
    request: SegmentationPreviewRequest = ...,
    user_info = Depends(get_current_user_with_token)
):
    """预览小说分段效果"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Previewing novel segmentation", 
                   novel_id=novel_id, user_id=user_id, mode=request.config.primary_segmentation_mode)
        
        # 验证请求中的novel_id与路径参数一致
        if request.novel_id != novel_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请求中的小说ID与路径参数不匹配"
            )
        
        result = await novel_service.preview_novel_segmentation(
            novel_id, user_id, request.config, request.max_segments
        )
        
        return SegmentationPreviewResponse(
            success=True,
            message="分段预览成功",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing novel segmentation: {e}", 
                   novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"预览分段失败: {str(e)}"
        )


@router.post("/{novel_id}/segmentation", response_model=SegmentationResponse)
async def segment_novel(
    novel_id: str = Path(..., description="小说ID"),
    request: SegmentationRequest = ...,
    user_info = Depends(get_current_user_with_token)
):
    """执行小说分段处理"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Starting novel segmentation", 
                   novel_id=novel_id, user_id=user_id, mode=request.config.primary_segmentation_mode)
        
        # 验证请求中的novel_id与路径参数一致
        if request.novel_id != novel_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请求中的小说ID与路径参数不匹配"
            )
        
        result = await novel_service.segment_novel(novel_id, user_id, request.config)
        
        return SegmentationResponse(
            success=True,
            message="分段处理成功",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error segmenting novel: {e}", 
                   novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分段处理失败: {str(e)}"
        )


@router.get("/{novel_id}/segmentation/stats", response_model=SegmentationStatsResponse)
async def get_novel_segmentation_stats(
    novel_id: str = Path(..., description="小说ID"),
    user_info = Depends(get_current_user_with_token)
):
    """获取小说分段统计信息"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting novel segmentation stats", novel_id=novel_id, user_id=user_id)
        
        result = await novel_service.get_novel_segmentation_stats(novel_id, user_id)
        
        return SegmentationStatsResponse(
            success=True,
            message="获取统计信息成功",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting novel segmentation stats: {e}", 
                   novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取统计信息失败: {str(e)}"
        )


@router.get("/{novel_id}/segments")
async def get_novel_segments(
    novel_id: str = Path(..., description="小说ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(100, ge=1, le=2000, description="每页数量"),
    user_info = Depends(get_current_user_with_token)
):
    """获取小说的分段列表"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting novel segments", novel_id=novel_id, user_id=user_id, page=page)
        
        segments, total = await novel_service.get_novel_segments(
            novel_id, user_id, page, page_size, access_token
        )
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "success": True,
            "message": "获取分段列表成功",
            "data": {
                "segments": segments,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting novel segments: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分段列表失败: {str(e)}"
        )


# ================================
# 阅读进度相关接口
# ================================

@router.get("/{novel_id}/progress", response_model=GetProgressResponse)
async def get_novel_progress(
    novel_id: str = Path(..., description="小说ID"),
    user_info = Depends(get_current_user_with_token)
):
    """获取用户在特定小说中的阅读进度"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting novel progress", novel_id=novel_id, user_id=user_id)
        
        progress = await novel_service.get_user_novel_progress(novel_id, user_id, access_token)
        
        return GetProgressResponse(
            success=True,
            message="获取阅读进度成功" if progress else "暂无阅读进度",
            data=progress
        )
        
    except Exception as e:
        logger.error(f"Error getting novel progress: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取阅读进度失败: {str(e)}"
        )


@router.put("/{novel_id}/progress", response_model=UpdateProgressResponse)
async def update_novel_progress(
    novel_id: str = Path(..., description="小说ID"),
    progress_data: UpdateProgressRequest = ...,
    user_info = Depends(get_current_user_with_token)
):
    """更新用户在特定小说中的阅读进度"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Updating novel progress", 
                   novel_id=novel_id, user_id=user_id, 
                   progress=progress_data.progress_percentage,
                   segment=progress_data.last_read_segment_id)
        
        progress = await novel_service.update_user_novel_progress(
            novel_id, user_id, progress_data, access_token
        )
        
        return UpdateProgressResponse(
            success=True,
            message="阅读进度更新成功",
            data=progress
        )
        
    except Exception as e:
        logger.error(f"Error updating novel progress: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新阅读进度失败: {str(e)}"
        )


@router.delete("/{novel_id}/progress")
async def delete_novel_progress(
    novel_id: str = Path(..., description="小说ID"),
    user_info = Depends(get_current_user_with_token)
):
    """删除用户在特定小说中的阅读进度"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Deleting novel progress", novel_id=novel_id, user_id=user_id)
        
        success = await novel_service.delete_user_novel_progress(novel_id, user_id, access_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="阅读进度不存在"
            )
        
        return {
            "success": True,
            "message": "阅读进度删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting novel progress: {e}", novel_id=novel_id, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除阅读进度失败: {str(e)}"
        )


@router.get("/progress/all", response_model=UserNovelProgressListResponse)
async def get_all_novel_progress(
    user_info = Depends(get_current_user_with_token)
):
    """获取用户所有小说的阅读进度"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting all novel progress", user_id=user_id)
        
        progress_list = await novel_service.get_user_all_novel_progress(user_id, access_token)
        
        return UserNovelProgressListResponse(
            success=True,
            message="获取阅读进度列表成功",
            data=progress_list,
            total=len(progress_list)
        )
        
    except Exception as e:
        logger.error(f"Error getting all novel progress: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取阅读进度列表失败: {str(e)}"
        )


@router.get("/progress/with-info", response_model=UserNovelProgressWithInfoResponse)
async def get_novel_progress_with_info(
    user_info = Depends(get_current_user_with_token)
):
    """获取用户所有小说的阅读进度（包含小说信息）"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting novel progress with info", user_id=user_id)
        
        progress_list = await novel_service.get_user_novel_progress_with_info(user_id, access_token)
        
        return UserNovelProgressWithInfoResponse(
            success=True,
            message="获取阅读进度列表成功",
            data=progress_list,
            total=len(progress_list)
        )
        
    except Exception as e:
        logger.error(f"Error getting novel progress with info: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取阅读进度列表失败: {str(e)}"
        )


@router.get("/reading-stats", response_model=ReadingStatsResponse)
async def get_reading_stats(
    user_info = Depends(get_current_user_with_token)
):
    """获取用户阅读统计信息"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting reading stats", user_id=user_id)
        
        stats = await novel_service.get_user_reading_stats(user_id, access_token)
        
        return ReadingStatsResponse(
            success=True,
            message="获取阅读统计成功",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting reading stats: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取阅读统计失败: {str(e)}"
        )