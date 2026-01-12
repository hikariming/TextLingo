from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.services.app_billing_service import AppBillingService
from app.schemas.app_billing import (
    AppSubscriptionStatus,
    UserFreePeriodCreate,
    BillingConfigUpdate,
    AppBillingStatsResponse
)
from app.core.dependencies import get_current_user

router = APIRouter()


@router.get("/status", response_model=AppSubscriptionStatus)
async def get_user_subscription_status(current_user = Depends(get_current_user)):
    """
    获取当前用户的订阅状态
    
    返回用户是否可以使用各项功能，包括：
    - 全局计费开关状态
    - 用户付费订阅状态  
    - 用户免费期状态
    - 可用功能列表
    - 功能限制信息
    """
    service = AppBillingService()
    return await service.get_user_subscription_status(current_user.id)


@router.get("/check-feature/{feature_name}")
async def check_feature_access(
    feature_name: str,
    current_user = Depends(get_current_user)
):
    """
    检查用户是否可以访问特定功能
    
    Args:
        feature_name: 功能名称 (如: ai_translation, novel_upload, etc.)
    
    Returns:
        是否可以访问该功能及相关限制信息
    """
    service = AppBillingService()
    status = await service.get_user_subscription_status(current_user.id)
    
    # 如果计费未启用，所有功能都可用
    if not status.billing_enabled:
        return {
            "allowed": True,
            "reason": "产品免费期间",
            "restrictions": {}
        }
    
    # 如果是付费用户或在免费期内，所有功能都可用
    if status.has_premium_subscription or status.is_in_free_period:
        return {
            "allowed": True,
            "reason": "付费用户" if status.has_premium_subscription else "免费期用户",
            "restrictions": {}
        }
    
    # 检查免费用户的功能权限
    allowed = feature_name in status.available_features or "all" in status.available_features
    restrictions = status.restrictions.get(feature_name, {})
    
    return {
        "allowed": allowed,
        "reason": "功能检查",
        "restrictions": restrictions
    }


@router.post("/grant-early-access")
async def grant_early_user_access(
    user_id: str,
    end_date: datetime,
    reason: str = "早期用户福利",
    current_user = Depends(get_current_user)
):
    """
    给指定用户授予早期用户免费访问权限
    
    需要管理员权限
    """
    # TODO: 添加管理员权限检查
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="需要管理员权限")
    
    service = AppBillingService()
    result = await service.grant_early_user_access(user_id, end_date, reason)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/grant-trial")
async def grant_trial_access(
    user_id: str,
    trial_days: int = 90,
    current_user = Depends(get_current_user)
):
    """
    给指定用户授予试用期访问权限
    
    Args:
        user_id: 用户ID
        trial_days: 试用期天数，默认90天
    """
    # TODO: 添加管理员权限检查或自动触发逻辑
    
    service = AppBillingService()
    result = await service.grant_trial_access(user_id, trial_days)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.post("/batch-grant-early-access")
async def batch_grant_early_access(
    end_date: datetime,
    reason: str = "早期用户福利批量授权",
    current_user = Depends(get_current_user)
):
    """
    批量给所有现有用户授予早期用户免费访问权限
    
    用于产品初期给所有早期用户授权
    """
    # TODO: 添加管理员权限检查
    
    service = AppBillingService()
    
    try:
        # 获取所有用户ID
        supabase = service.supabase
        users_response = supabase.from_("user_profiles").select("user_id").execute()
        
        if not users_response.data:
            return {"success": True, "message": "没有找到用户", "granted_count": 0}
        
        granted_count = 0
        failed_count = 0
        errors = []
        
        for user in users_response.data:
            user_id = user["user_id"]
            result = await service.grant_early_user_access(user_id, end_date, reason)
            
            if result["success"]:
                granted_count += 1
            else:
                failed_count += 1
                errors.append(f"用户 {user_id}: {result['error']}")
        
        return {
            "success": True,
            "message": f"批量授权完成",
            "granted_count": granted_count,
            "failed_count": failed_count,
            "errors": errors[:10]  # 只返回前10个错误
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量授权失败: {str(e)}"
        )


@router.put("/config")
async def update_billing_config(
    config_update: BillingConfigUpdate,
    current_user = Depends(get_current_user)
):
    """
    更新计费配置
    
    可以更新的配置项：
    - billing_enabled: 是否启用计费
    - free_period_end_date: 全局免费期结束日期
    - trial_period_days: 新用户试用期天数
    - grace_period_days: 宽限期天数
    """
    # TODO: 添加管理员权限检查
    
    service = AppBillingService()
    result = await service.update_billing_config(config_update)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )
    
    return result


@router.get("/stats")
async def get_billing_stats(current_user = Depends(get_current_user)):
    """
    获取计费相关统计信息
    
    包括：
    - 总用户数
    - 付费用户数
    - 各类免费期用户数
    - 转化率
    """
    # TODO: 添加管理员权限检查
    
    service = AppBillingService()
    result = await service.get_billing_stats()
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return result["data"]


@router.get("/config")
async def get_billing_config(current_user = Depends(get_current_user)):
    """获取当前计费配置"""
    # TODO: 添加管理员权限检查
    
    service = AppBillingService()
    
    try:
        response = service.supabase.from_("app_billing_config")\
            .select("*")\
            .eq("is_active", True)\
            .execute()
        
        return {"configs": response.data or []}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


# 中间件装饰器，用于在其他API中检查订阅状态
async def require_feature_access(feature_name: str, user_id: str) -> bool:
    """
    检查用户是否有特定功能的访问权限
    
    可以在其他API端点中使用这个函数来检查权限
    """
    service = AppBillingService()
    status = await service.get_user_subscription_status(user_id)
    
    # 如果计费未启用，所有功能都可用
    if not status.billing_enabled:
        return True
    
    # 如果是付费用户或在免费期内，所有功能都可用
    if status.has_premium_subscription or status.is_in_free_period:
        return True
    
    # 检查免费用户的功能权限
    return feature_name in status.available_features or "all" in status.available_features


# 使用示例：在其他API中检查权限
"""
# 在其他API端点中使用：

@router.post("/some-premium-feature")
async def some_premium_feature(current_user = Depends(get_current_user)):
    # 检查功能权限
    has_access = await require_feature_access("premium_feature", current_user.id)
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="此功能需要付费订阅"
        )
    
    # 执行功能逻辑...
    return {"message": "功能执行成功"}
"""