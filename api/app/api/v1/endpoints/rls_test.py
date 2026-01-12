from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
import uuid

from app.core.dependencies import get_current_user_with_token
from app.schemas.auth import UserResponse
from app.schemas.rls_test import (
    RlsTestDataCreate,
    RlsTestDataUpdate,
    RlsTestDataResponse,
    RlsTestDataListResponse,
    RlsTestStats
)
from app.services.rls_test_service import RlsTestService

router = APIRouter()

rls_test_service = RlsTestService()


@router.post("/", response_model=RlsTestDataResponse, status_code=status.HTTP_201_CREATED)
async def create_rls_test_data(
    data: RlsTestDataCreate,
    user_info: tuple = Depends(get_current_user_with_token)
) -> RlsTestDataResponse:
    """
    创建RLS测试数据
    
    测试RLS创建权限：
    - 只能创建属于自己的数据
    - 自动设置user_id为当前用户
    """
    current_user, access_token = user_info
    
    try:
        result = await rls_test_service.create_test_data(current_user.id, data, access_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建RLS测试数据失败: {str(e)}"
        )


@router.get("/", response_model=RlsTestDataListResponse)
async def list_rls_test_data(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    is_private: Optional[bool] = Query(None, description="过滤私有/公共数据"),
    user_info: tuple = Depends(get_current_user_with_token)
) -> RlsTestDataListResponse:
    """
    获取用户的RLS测试数据列表
    
    测试RLS查询权限：
    - 只能查看属于自己的数据
    - 支持分页和过滤
    """
    current_user, access_token = user_info
    
    try:
        result = await rls_test_service.list_test_data(
            user_id=current_user.id,
            access_token=access_token,
            page=page,
            per_page=per_page,
            is_private=is_private
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取RLS测试数据列表失败: {str(e)}"
        )


@router.get("/{data_id}", response_model=RlsTestDataResponse)
async def get_rls_test_data(
    data_id: int,
    user_info: tuple = Depends(get_current_user_with_token)
) -> RlsTestDataResponse:
    """
    根据ID获取RLS测试数据
    
    测试RLS查询权限：
    - 只能查看属于自己的数据
    - 尝试访问其他用户数据会返回404
    """
    current_user, access_token = user_info
    
    try:
        result = await rls_test_service.get_test_data_by_id(current_user.id, data_id, access_token)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RLS测试数据未找到或无权限访问"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取RLS测试数据失败: {str(e)}"
        )


@router.put("/{data_id}", response_model=RlsTestDataResponse)
async def update_rls_test_data(
    data_id: int,
    data: RlsTestDataUpdate,
    user_info: tuple = Depends(get_current_user_with_token)
) -> RlsTestDataResponse:
    """
    更新RLS测试数据
    
    测试RLS更新权限：
    - 只能更新属于自己的数据
    - 尝试更新其他用户数据会返回404
    """
    current_user, access_token = user_info
    
    try:
        result = await rls_test_service.update_test_data(current_user.id, data_id, data, access_token)
        
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RLS测试数据未找到或无权限修改"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"更新RLS测试数据失败: {str(e)}"
        )


@router.delete("/{data_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rls_test_data(
    data_id: int,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    删除RLS测试数据
    
    测试RLS删除权限：
    - 只能删除属于自己的数据
    - 尝试删除其他用户数据会返回404
    """
    current_user, access_token = user_info
    
    try:
        success = await rls_test_service.delete_test_data(current_user.id, data_id, access_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RLS测试数据未找到或无权限删除"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"删除RLS测试数据失败: {str(e)}"
        )


@router.get("/stats/summary", response_model=RlsTestStats)
async def get_rls_test_stats(
    user_info: tuple = Depends(get_current_user_with_token)
) -> RlsTestStats:
    """
    获取用户的RLS测试数据统计信息
    
    测试RLS统计权限：
    - 只能查看属于自己的数据统计
    - 统计信息只包含当前用户的数据
    """
    current_user, access_token = user_info
    
    try:
        result = await rls_test_service.get_test_stats(current_user.id, access_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取RLS测试数据统计失败: {str(e)}"
        )


@router.post("/permissions/test", response_model=Dict[str, Any])
async def test_rls_permissions(
    user_info: tuple = Depends(get_current_user_with_token)
) -> Dict[str, Any]:
    """
    执行完整的RLS权限测试
    
    测试内容：
    1. 创建数据权限
    2. 读取数据权限
    3. 更新数据权限
    4. 删除数据权限
    
    返回详细的测试结果和错误信息，用于调试RLS配置
    """
    current_user, access_token = user_info
    
    try:
        result = await rls_test_service.test_rls_permissions(current_user.id, access_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"RLS权限测试失败: {str(e)}"
        )


@router.get("/debug/client-info", response_model=Dict[str, Any])
async def get_client_debug_info(
    user_info: tuple = Depends(get_current_user_with_token)
) -> Dict[str, Any]:
    """
    获取客户端调试信息
    
    用于调试RLS配置，返回：
    - 当前用户信息
    - 客户端配置信息
    - 权限上下文信息
    """
    current_user, access_token = user_info
    
    try:
        # 获取基本调试信息
        debug_info = {
            "user": {
                "id": str(current_user.id),
                "email": current_user.email,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None
            },
            "client": {
                "has_access_token": access_token is not None,
                "token_length": len(access_token) if access_token else 0,
                "using_user_client": True
            },
            "rls": {
                "enabled": True,
                "expected_user_id": str(current_user.id)
            }
        }
        
        # 尝试基本的数据库连接测试
        try:
            stats = await rls_test_service.get_test_stats(current_user.id, access_token)
            debug_info["database"] = {
                "connection": "success",
                "records_visible": stats.total_records
            }
        except Exception as e:
            debug_info["database"] = {
                "connection": "failed",
                "error": str(e)
            }
        
        return debug_info
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"获取调试信息失败: {str(e)}"
        ) 