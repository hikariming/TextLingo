from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Header
from typing import List, Optional
from app.services.material_service import material_service
from app.schemas.material_schemas import (
    MaterialLibraryCreate, MaterialLibraryUpdate, MaterialLibraryResponse,
    MaterialArticleCreate, MaterialArticleUpdate, MaterialArticleResponse,
    MaterialSegmentCreate, MaterialSegmentUpdate, MaterialSegmentResponse,
    MaterialLibraryQuery, MaterialArticleQuery, MaterialSegmentBatchCreate,
    MaterialLibraryListResponse, MaterialArticleListResponse, MaterialSegmentListResponse
)
from app.schemas.auth import UserResponse
from app.core.dependencies import get_current_user, get_current_user_with_token
import structlog

logger = structlog.get_logger()

router = APIRouter()

# 文章库相关端点
@router.post("/libraries", response_model=MaterialLibraryResponse, status_code=status.HTTP_201_CREATED)
async def create_library(
    library_data: MaterialLibraryCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """创建文章库"""
    try:
        user_id = current_user.id
        library = await material_service.create_library(user_id, library_data)
        return library
    except Exception as e:
        logger.error(f"Error creating library: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create library"
        )

@router.get("/libraries", response_model=MaterialLibraryListResponse)
async def list_libraries(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    library_type: Optional[str] = Query(None),
    is_public: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user)
):
    """获取文章库列表"""
    try:
        user_id = current_user.id
        query = MaterialLibraryQuery(
            page=page,
            page_size=page_size,
            library_type=library_type,
            is_public=is_public,
            search=search
        )
        libraries, total = await material_service.list_libraries(user_id, query)
        
        total_pages = (total + page_size - 1) // page_size
        
        return MaterialLibraryListResponse(
            items=libraries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error listing libraries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list libraries"
        )

@router.get("/libraries/{library_id}", response_model=MaterialLibraryResponse)
async def get_library(
    library_id: str = Path(..., description="Library ID"),
    current_user: UserResponse = Depends(get_current_user)
):
    """获取单个文章库"""
    try:
        user_id = current_user.id
        library = await material_service.get_library(user_id, library_id)
        
        if not library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library not found"
            )
        
        return library
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting library: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get library"
        )

@router.put("/libraries/{library_id}", response_model=MaterialLibraryResponse)
async def update_library(
    library_data: MaterialLibraryUpdate,
    library_id: str = Path(..., description="Library ID"),
    current_user: UserResponse = Depends(get_current_user)
):
    """更新文章库"""
    try:
        user_id = current_user.id
        library = await material_service.update_library(user_id, library_id, library_data)
        
        if not library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library not found or no permission"
            )
        
        return library
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating library: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update library"
        )

@router.delete("/libraries/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(
    library_id: str = Path(..., description="Library ID"),
    current_user: UserResponse = Depends(get_current_user)
):
    """删除文章库"""
    try:
        user_id = current_user.id
        success = await material_service.delete_library(user_id, library_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Library not found or no permission"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting library: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete library"
        )

# 文章相关端点
@router.post("/articles", response_model=MaterialArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_data: MaterialArticleCreate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """创建文章"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        article = await material_service.create_article(user_id, article_data, access_token)
        return article
    except Exception as e:
        logger.error(f"Error creating article: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create article"
        )

@router.get("/articles", response_model=MaterialArticleListResponse)
async def list_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    library_id: Optional[str] = Query(None),
    article_status: Optional[str] = Query(None, alias="status"),
    is_public: Optional[bool] = Query(None),
    difficulty_level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取文章列表"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        query = MaterialArticleQuery(
            page=page,
            page_size=page_size,
            library_id=library_id,
            status=article_status,
            is_public=is_public,
            difficulty_level=difficulty_level,
            category=category,
            search=search
        )
        articles, total = await material_service.list_articles(user_id, query, access_token)
        
        total_pages = (total + page_size - 1) // page_size
        
        return MaterialArticleListResponse(
            items=articles,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error listing articles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list articles"
        )

@router.get("/articles/{article_id}", response_model=MaterialArticleResponse)
async def get_article(
    article_id: str = Path(..., description="Article ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取单个文章"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        article = await material_service.get_article(user_id, article_id, access_token)
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found"
            )
        
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get article"
        )

@router.put("/articles/{article_id}", response_model=MaterialArticleResponse)
async def update_article(
    article_data: MaterialArticleUpdate,
    article_id: str = Path(..., description="Article ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """更新文章"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        article = await material_service.update_article(user_id, article_id, article_data, access_token)
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or no permission"
            )
        
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating article: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update article"
        )

@router.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: str = Path(..., description="Article ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """删除文章"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        success = await material_service.delete_article(user_id, article_id, access_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or no permission"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting article: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete article"
        )

# 文章分段相关端点
@router.post("/segments", response_model=MaterialSegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    segment_data: MaterialSegmentCreate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """创建文章分段"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        segment = await material_service.create_segment(user_id, segment_data, access_token)
        return segment
    except Exception as e:
        logger.error(f"Error creating segment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create segment"
        )

@router.post("/segments/batch", response_model=List[MaterialSegmentResponse], status_code=status.HTTP_201_CREATED)
async def create_segments_batch(
    batch_data: MaterialSegmentBatchCreate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """批量创建文章分段"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        segments = await material_service.create_segments_batch(user_id, batch_data, access_token)
        return segments
    except Exception as e:
        logger.error(f"Error creating segments batch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create segments"
        )

@router.get("/articles/{article_id}/segments", response_model=MaterialSegmentListResponse)
async def get_article_segments(
    article_id: str = Path(..., description="Article ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取文章的分段列表"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        segments, total = await material_service.get_article_segments(user_id, article_id, page, page_size, access_token)
        
        total_pages = (total + page_size - 1) // page_size
        
        return MaterialSegmentListResponse(
            items=segments,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    except Exception as e:
        logger.error(f"Error getting article segments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get article segments"
        )

@router.put("/segments/{segment_id}", response_model=MaterialSegmentResponse)
async def update_segment(
    segment_data: MaterialSegmentUpdate,
    segment_id: str = Path(..., description="Segment ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """更新文章分段"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        segment = await material_service.update_segment(user_id, segment_id, segment_data, access_token)
        
        if not segment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Segment not found or no permission"
            )
        
        return segment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating segment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update segment"
        )

@router.delete("/segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_segment(
    segment_id: str = Path(..., description="Segment ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """删除文章分段"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        success = await material_service.delete_segment(user_id, segment_id, access_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Segment not found or no permission"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting segment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete segment"
        )

# 文章文本分段辅助端点
@router.post("/articles/{article_id}/auto-segment", response_model=List[MaterialSegmentResponse])
async def auto_segment_article(
    article_id: str = Path(..., description="Article ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """自动将文章分段（按句号和换行符分段）"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        # 使用新的段落分段方法
        segments = await material_service.auto_segment_article_by_paragraph(user_id, article_id, access_token)
        return segments
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-segmenting article: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to auto-segment article"
        ) 