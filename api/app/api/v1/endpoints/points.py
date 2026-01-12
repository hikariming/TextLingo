from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.dependencies import get_current_user
from app.services import points_service
from app.schemas import (
    UserResponse,
    ConsumePointsRequest,
    ConsumePointsResponse,
    RechargePointsRequest,
    RechargePointsResponse,
    UserPointsBalance,
    PointPricingConfig,
    CalculatePointsRequest,
    CalculatePointsResponse,
    PointTransactionQuery,
    PointTransactionHistoryResponse,
    ServiceType,
    TransactionType,
    TransactionStatus
)

router = APIRouter()


@router.get("/balance", response_model=UserPointsBalance)
async def get_user_points_balance(
    current_user: UserResponse = Depends(get_current_user)
):
    """获取当前用户的积分余额"""
    balance = await points_service.get_user_balance(current_user.id)
    
    if balance is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="无法获取积分余额"
        )
    
    return balance


@router.post("/calculate", response_model=CalculatePointsResponse)
async def calculate_points_required(
    request: CalculatePointsRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """计算执行操作所需的积分"""
    calculation = await points_service.calculate_points_required(request)
    
    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到相应的定价配置"
        )
    
    return calculation


@router.post("/consume", response_model=ConsumePointsResponse)
async def consume_points(
    request: ConsumePointsRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """消费积分"""
    result = await points_service.consume_points(current_user.id, request)
    
    if not result.success:
        # 根据错误类型返回不同的HTTP状态码
        if result.error == "insufficient_points":
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=result.message or "积分不足"
            )
        elif result.error == "pricing_not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result.message or "未找到定价配置"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.message or "积分消费失败"
            )
    
    return result


@router.post("/recharge", response_model=RechargePointsResponse)
async def recharge_points(
    request: RechargePointsRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """充值积分"""
    result = await points_service.recharge_points(current_user.id, request)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="积分充值失败"
        )
    
    return result


@router.get("/history", response_model=PointTransactionHistoryResponse)
async def get_transaction_history(
    transaction_type: Optional[TransactionType] = Query(None, description="交易类型过滤"),
    service_type: Optional[ServiceType] = Query(None, description="服务类型过滤"),
    transaction_status: Optional[TransactionStatus] = Query(None, description="状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    current_user: UserResponse = Depends(get_current_user)
):
    """获取用户的积分交易历史"""
    query = PointTransactionQuery(
        transaction_type=transaction_type,
        service_type=service_type,
        status=transaction_status,
        page=page,
        page_size=page_size
    )
    
    history = await points_service.get_transaction_history(current_user.id, query)
    
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="无法获取交易历史"
        )
    
    return history


@router.get("/pricing", response_model=list[PointPricingConfig])
async def get_pricing_configs():
    """获取所有定价配置"""
    configs = await points_service.get_pricing_configs()
    return configs


@router.get("/check-sufficient")
async def check_sufficient_points(
    service_type: ServiceType = Query(..., description="服务类型"),
    aimodel_name: Optional[str] = Query(None, description="模型名称"),
    tokens_used: int = Query(0, ge=0, description="预计使用的token数量"),
    current_user: UserResponse = Depends(get_current_user)
):
    """检查用户积分是否足够执行指定操作"""
    result = await points_service.check_sufficient_points(
        current_user.id, 
        service_type, 
        aimodel_name, 
        tokens_used
    )
    
    return result


# 管理员端点（需要额外的权限检查）
@router.post("/admin/grant", response_model=RechargePointsResponse)
async def admin_grant_points(
    user_id: str,
    points: int,
    reason: str = "管理员赠送",
    current_user: UserResponse = Depends(get_current_user)
):
    """管理员给用户赠送积分"""
    # TODO: 添加管理员权限检查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    
    request = RechargePointsRequest(
        points_to_add=points,
        description=f"管理员赠送: {reason}",
        request_id=f"admin_grant_{current_user.id}"
    )
    
    result = await points_service.recharge_points(user_id, request)
    
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="积分赠送失败"
        )
    
    return result