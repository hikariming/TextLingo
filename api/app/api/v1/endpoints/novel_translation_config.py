"""
小说用户翻译配置API端点
处理用户对每本小说的个性化翻译和阅读设置
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Body
from typing import List, Optional
from app.services.novel_translation_config_service import NovelTranslationConfigService
from app.schemas.novel_translation_config_schemas import (
    NovelTranslationConfigCreate, NovelTranslationConfigUpdate,
    NovelTranslationConfigCreateResponse, NovelTranslationConfigUpdateResponse,
    NovelTranslationConfigGetResponse, NovelTranslationConfigListResponse,
    NovelTranslationConfigDeleteResponse, NovelTranslationConfigBatchRequest,
    NovelTranslationConfigBatchResponse
)
from app.core.dependencies import get_current_user_with_token
import structlog

logger = structlog.get_logger()

router = APIRouter()

# 初始化服务
config_service = NovelTranslationConfigService()


# ================================
# 翻译配置 CRUD 操作
# ================================

@router.post("/", response_model=NovelTranslationConfigCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_translation_config(
    config_data: NovelTranslationConfigCreate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """创建或更新翻译配置（UPSERT操作）"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info(
            "Creating/updating translation config", 
            user_id=user_id, 
            novel_id=config_data.novel_id
        )
        
        config = await config_service.create_or_update_config(user_id, config_data, access_token)
        
        return NovelTranslationConfigCreateResponse(
            success=True,
            message="翻译配置保存成功",
            data=config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"Error creating/updating translation config: {type(e).__name__}: {str(e)}"
        logger.error(error_detail, user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存翻译配置失败: {error_detail}"
        )


@router.get("/{novel_id}", response_model=NovelTranslationConfigGetResponse)
async def get_translation_config(
    novel_id: str = Path(..., description="小说ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户对特定小说的翻译配置"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting translation config", user_id=user_id, novel_id=novel_id)
        
        config = await config_service.get_config(user_id, novel_id, access_token)
        
        return NovelTranslationConfigGetResponse(
            success=True,
            message="获取翻译配置成功" if config else "未找到翻译配置",
            data=config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting translation config: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取翻译配置失败: {str(e)}"
        )


@router.put("/{novel_id}", response_model=NovelTranslationConfigUpdateResponse)
async def update_translation_config(
    novel_id: str = Path(..., description="小说ID"),
    config_update: NovelTranslationConfigUpdate = Body(...),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """更新翻译配置"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Updating translation config", user_id=user_id, novel_id=novel_id)
        
        config = await config_service.update_config(user_id, novel_id, config_update, access_token)
        
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到要更新的翻译配置"
            )
        
        return NovelTranslationConfigUpdateResponse(
            success=True,
            message="翻译配置更新成功",
            data=config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating translation config: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新翻译配置失败: {str(e)}"
        )


@router.delete("/{novel_id}", response_model=NovelTranslationConfigDeleteResponse)
async def delete_translation_config(
    novel_id: str = Path(..., description="小说ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """删除翻译配置"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Deleting translation config", user_id=user_id, novel_id=novel_id)
        
        success = await config_service.delete_config(user_id, novel_id, access_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到要删除的翻译配置"
            )
        
        return NovelTranslationConfigDeleteResponse(
            success=True,
            message="翻译配置删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting translation config: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"删除翻译配置失败: {str(e)}"
        )


@router.get("/", response_model=NovelTranslationConfigListResponse)
async def get_user_translation_configs(
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户的所有翻译配置"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info("Getting user translation configs", user_id=user_id, limit=limit, offset=offset)
        
        configs = await config_service.get_user_configs(user_id, access_token, limit, offset)
        
        return NovelTranslationConfigListResponse(
            success=True,
            message=f"获取翻译配置成功，共 {len(configs)} 条",
            data=configs,
            total=len(configs)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user translation configs: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取翻译配置列表失败: {str(e)}"
        )


@router.post("/batch", response_model=NovelTranslationConfigBatchResponse)
async def get_batch_translation_configs(
    request: NovelTranslationConfigBatchRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """批量获取用户对多本小说的翻译配置"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        logger.info(
            "Getting batch translation configs", 
            user_id=user_id, 
            novel_count=len(request.novel_ids)
        )
        
        configs = await config_service.get_batch_configs(user_id, request.novel_ids, access_token)
        
        return NovelTranslationConfigBatchResponse(
            success=True,
            message=f"批量获取翻译配置成功，请求 {len(request.novel_ids)} 本小说",
            data=configs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch translation configs: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"批量获取翻译配置失败: {str(e)}"
        )


@router.post("/{novel_id}/touch", status_code=status.HTTP_200_OK)
async def touch_translation_config(
    novel_id: str = Path(..., description="小说ID"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """更新翻译配置的最后使用时间"""
    try:
        current_user, access_token = user_info
        user_id = current_user.id
        
        success = await config_service.update_last_used(user_id, novel_id, access_token)
        
        return {
            "success": success,
            "message": "最后使用时间更新成功" if success else "未找到配置"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error touching translation config: {e}", user_id=user_id if 'user_id' in locals() else None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新使用时间失败: {str(e)}"
        )