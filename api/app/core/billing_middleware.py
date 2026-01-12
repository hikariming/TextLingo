from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status
from app.services.app_billing_service import AppBillingService
import structlog

logger = structlog.get_logger()


def require_billing_feature(feature_name: str):
    """
    装饰器：检查用户是否有特定功能的访问权限
    
    Args:
        feature_name: 功能名称
        
    Usage:
        @require_billing_feature("ai_translation")
        async def translate_text(text: str, current_user = Depends(get_current_user)):
            # 功能实现
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 从kwargs中获取current_user
            current_user = None
            for key, value in kwargs.items():
                if hasattr(value, 'id') and hasattr(value, 'email'):
                    current_user = value
                    break
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="需要用户认证"
                )
            
            # 检查功能权限
            billing_service = AppBillingService()
            subscription_status = await billing_service.get_user_subscription_status(current_user.id)
            
            # 如果计费未启用，允许所有功能
            if not subscription_status.billing_enabled:
                return await func(*args, **kwargs)
            
            # 如果是付费用户或在免费期内，允许所有功能
            if subscription_status.has_premium_subscription or subscription_status.is_in_free_period:
                return await func(*args, **kwargs)
            
            # 检查免费用户的功能权限
            has_access = (
                feature_name in subscription_status.available_features or 
                "all" in subscription_status.available_features
            )
            
            if not has_access:
                # 获取功能限制信息
                restrictions = subscription_status.restrictions.get(feature_name, {})
                
                error_detail = f"功能 '{feature_name}' 需要付费订阅"
                if restrictions.get("daily_limit"):
                    error_detail += f"，免费用户每日限制 {restrictions['daily_limit']} 次"
                
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=error_detail
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


async def check_feature_usage_limit(user_id: str, feature_name: str) -> dict:
    """
    检查用户功能使用限制
    
    Args:
        user_id: 用户ID
        feature_name: 功能名称
        
    Returns:
        包含限制信息的字典
    """
    billing_service = AppBillingService()
    subscription_status = await billing_service.get_user_subscription_status(user_id)
    
    # 如果计费未启用或用户有付费订阅/免费期，无限制
    if (not subscription_status.billing_enabled or 
        subscription_status.has_premium_subscription or 
        subscription_status.is_in_free_period):
        return {
            "has_limit": False,
            "daily_limit": None,
            "monthly_limit": None,
            "remaining_daily": None,
            "remaining_monthly": None
        }
    
    # 获取功能限制
    restrictions = subscription_status.restrictions.get(feature_name, {})
    
    if not restrictions.get("allowed", False):
        return {
            "has_limit": True,
            "allowed": False,
            "reason": "功能不可用"
        }
    
    daily_limit = restrictions.get("daily_limit")
    monthly_limit = restrictions.get("monthly_limit")
    
    if not daily_limit and not monthly_limit:
        return {
            "has_limit": False,
            "daily_limit": None,
            "monthly_limit": None
        }
    
    # TODO: 实现使用次数统计逻辑
    # 这里需要查询用户今日/本月的使用次数
    # 可以创建一个 user_feature_usage 表来记录使用情况
    
    return {
        "has_limit": True,
        "daily_limit": daily_limit,
        "monthly_limit": monthly_limit,
        "remaining_daily": daily_limit,  # 需要实际计算
        "remaining_monthly": monthly_limit,  # 需要实际计算
        "message": "功能使用受限，请考虑升级到付费版本"
    }


class BillingMiddleware:
    """计费中间件类"""
    
    def __init__(self):
        self.billing_service = AppBillingService()
    
    async def check_user_access(self, user_id: str, feature_name: str) -> bool:
        """检查用户是否有功能访问权限"""
        try:
            subscription_status = await self.billing_service.get_user_subscription_status(user_id)
            
            # 如果计费未启用，允许所有功能
            if not subscription_status.billing_enabled:
                return True
            
            # 如果是付费用户或在免费期内，允许所有功能
            if subscription_status.has_premium_subscription or subscription_status.is_in_free_period:
                return True
            
            # 检查免费用户的功能权限
            return (
                feature_name in subscription_status.available_features or 
                "all" in subscription_status.available_features
            )
            
        except Exception as e:
            logger.error(f"检查用户访问权限失败: {e}")
            # 出错时默认允许访问，避免影响用户体验
            return True
    
    async def get_feature_restrictions(self, user_id: str, feature_name: str) -> dict:
        """获取用户功能限制信息"""
        try:
            subscription_status = await self.billing_service.get_user_subscription_status(user_id)
            return subscription_status.restrictions.get(feature_name, {})
        except Exception as e:
            logger.error(f"获取功能限制失败: {e}")
            return {}


# 全局中间件实例
billing_middleware = BillingMiddleware()


# 便捷函数
async def require_feature_access(feature_name: str, user_id: str) -> bool:
    """
    检查用户是否有特定功能的访问权限
    
    这是一个便捷函数，可以在任何地方调用
    """
    return await billing_middleware.check_user_access(user_id, feature_name)


async def get_user_billing_status(user_id: str):
    """
    获取用户计费状态的便捷函数
    """
    billing_service = AppBillingService()
    return await billing_service.get_user_subscription_status(user_id)