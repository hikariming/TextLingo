from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import structlog
from app.services.supabase_client import supabase_service
from app.schemas.app_billing import (
    AppSubscriptionStatus, 
    UserFreePeriodCreate, 
    PeriodType,
    BillingConfigUpdate
)

logger = structlog.get_logger()


class AppBillingService:
    """App订阅和计费服务"""
    
    def __init__(self, access_token: str = None):
        if access_token:
            self.supabase = supabase_service.get_user_client(access_token)
        else:
            self.supabase = supabase_service.get_client()

    async def get_user_subscription_status(self, user_id: str) -> AppSubscriptionStatus:
        """获取用户完整的订阅状态"""
        try:
            # 1. 检查全局计费开关
            billing_enabled = await self._is_billing_enabled()
            
            # 如果计费未启用，所有用户都可以免费使用
            if not billing_enabled:
                return AppSubscriptionStatus(
                    user_id=user_id,
                    billing_enabled=False,
                    subscription_type="FREE",
                    available_features=["all"],
                    message="产品免费使用期间，所有功能免费开放"
                )
            
            # 2. 检查是否有付费订阅
            premium_subscription = await self._get_premium_subscription(user_id)
            if premium_subscription:
                return AppSubscriptionStatus(
                    user_id=user_id,
                    billing_enabled=True,
                    has_premium_subscription=True,
                    subscription_type="PREMIUM",
                    available_features=["all"],
                    message="高级订阅用户，享受全部功能"
                )
            
            # 3. 检查是否在免费期内
            free_period = await self._get_active_free_period(user_id)
            if free_period:
                return AppSubscriptionStatus(
                    user_id=user_id,
                    billing_enabled=True,
                    subscription_type=free_period["period_type"],
                    is_in_free_period=True,
                    free_period_end=datetime.fromisoformat(free_period["end_date"]),
                    free_period_reason=free_period["reason"],
                    available_features=["all"],
                    message=f"免费期用户，有效期至 {free_period['end_date']}"
                )
            
            # 4. 默认免费用户，功能受限
            return AppSubscriptionStatus(
                user_id=user_id,
                billing_enabled=True,
                subscription_type="FREE",
                available_features=await self._get_free_user_features(),
                restrictions=await self._get_free_user_restrictions(),
                message="免费用户，部分功能受限"
            )
            
        except Exception as e:
            logger.error(f"获取用户订阅状态失败: {e}")
            # 出错时返回安全的默认状态
            return AppSubscriptionStatus(
                user_id=user_id,
                billing_enabled=False,
                subscription_type="FREE",
                available_features=["basic"],
                message="系统错误，请稍后重试"
            )

    async def _is_billing_enabled(self) -> bool:
        """检查全局计费是否启用"""
        try:
            response = self.supabase.from_("app_billing_config")\
                .select("config_value")\
                .eq("config_key", "billing_enabled")\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if response.data:
                return response.data["config_value"].lower() == "true"
            return False
            
        except Exception as e:
            logger.error(f"检查计费状态失败: {e}")
            return False

    async def _get_premium_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户的付费订阅"""
        try:
            # 这里复用你现有的订阅服务
            from app.services.subscription_service import SubscriptionService
            subscription_service = SubscriptionService()
            return await subscription_service.get_user_subscription(user_id)
            
        except Exception as e:
            logger.error(f"获取付费订阅失败: {e}")
            return None

    async def _get_active_free_period(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户当前有效的免费期"""
        try:
            current_time = datetime.now().isoformat()
            
            response = self.supabase.from_("user_free_periods")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("is_active", True)\
                .lte("start_date", current_time)\
                .gte("end_date", current_time)\
                .order("end_date", desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"获取免费期失败: {e}")
            return None

    async def _get_free_user_features(self) -> List[str]:
        """获取免费用户可用功能列表"""
        try:
            response = self.supabase.from_("feature_restrictions")\
                .select("feature_name")\
                .eq("plan_type", "FREE")\
                .eq("is_allowed", True)\
                .execute()
            
            if response.data:
                return [item["feature_name"] for item in response.data]
            return ["basic_reading", "basic_translation"]
            
        except Exception as e:
            logger.error(f"获取免费用户功能失败: {e}")
            return ["basic_reading"]

    async def _get_free_user_restrictions(self) -> Dict[str, Any]:
        """获取免费用户功能限制"""
        try:
            response = self.supabase.from_("feature_restrictions")\
                .select("*")\
                .eq("plan_type", "FREE")\
                .execute()
            
            restrictions = {}
            if response.data:
                for item in response.data:
                    feature_name = item["feature_name"]
                    restrictions[feature_name] = {
                        "allowed": item["is_allowed"],
                        "daily_limit": item.get("daily_limit"),
                        "monthly_limit": item.get("monthly_limit")
                    }
            
            return restrictions
            
        except Exception as e:
            logger.error(f"获取用户限制失败: {e}")
            return {}

    async def create_user_free_period(self, free_period_data: UserFreePeriodCreate) -> Dict[str, Any]:
        """为用户创建免费期"""
        try:
            # 检查是否已存在同类型的免费期
            existing = await self._get_existing_free_period(
                free_period_data.user_id, 
                free_period_data.period_type
            )
            
            if existing:
                return {
                    "success": False,
                    "error": f"用户已存在 {free_period_data.period_type} 类型的免费期"
                }
            
            # 创建新的免费期
            response = self.supabase.from_("user_free_periods")\
                .insert({
                    "user_id": free_period_data.user_id,
                    "period_type": free_period_data.period_type,
                    "start_date": free_period_data.start_date.isoformat(),
                    "end_date": free_period_data.end_date.isoformat(),
                    "reason": free_period_data.reason
                })\
                .execute()
            
            if response.data:
                logger.info(f"为用户 {free_period_data.user_id} 创建免费期成功")
                return {"success": True, "data": response.data[0]}
            
            return {"success": False, "error": "创建免费期失败"}
            
        except Exception as e:
            logger.error(f"创建用户免费期失败: {e}")
            return {"success": False, "error": str(e)}

    async def _get_existing_free_period(self, user_id: str, period_type: PeriodType) -> Optional[Dict[str, Any]]:
        """检查用户是否已有指定类型的免费期"""
        try:
            response = self.supabase.from_("user_free_periods")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("period_type", period_type)\
                .eq("is_active", True)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"查询已存在免费期失败: {e}")
            return None

    async def grant_early_user_access(self, user_id: str, end_date: datetime, reason: str = "早期用户福利") -> Dict[str, Any]:
        """给用户授予早期用户免费访问权限"""
        free_period_data = UserFreePeriodCreate(
            user_id=user_id,
            period_type=PeriodType.EARLY_USER,
            start_date=datetime.now(),
            end_date=end_date,
            reason=reason
        )
        
        return await self.create_user_free_period(free_period_data)

    async def grant_trial_access(self, user_id: str, trial_days: int = 90) -> Dict[str, Any]:
        """给新用户授予试用期访问权限"""
        end_date = datetime.now() + timedelta(days=trial_days)
        
        free_period_data = UserFreePeriodCreate(
            user_id=user_id,
            period_type=PeriodType.TRIAL,
            start_date=datetime.now(),
            end_date=end_date,
            reason="新用户试用期"
        )
        
        return await self.create_user_free_period(free_period_data)

    async def update_billing_config(self, config_update: BillingConfigUpdate) -> Dict[str, Any]:
        """更新计费配置"""
        try:
            response = self.supabase.from_("app_billing_config")\
                .update({
                    "config_value": config_update.config_value,
                    "description": config_update.description,
                    "updated_at": datetime.now().isoformat()
                })\
                .eq("config_key", config_update.config_key)\
                .execute()
            
            if response.data:
                logger.info(f"更新计费配置成功: {config_update.config_key} = {config_update.config_value}")
                return {"success": True, "data": response.data[0]}
            
            return {"success": False, "error": "配置项不存在"}
            
        except Exception as e:
            logger.error(f"更新计费配置失败: {e}")
            return {"success": False, "error": str(e)}

    async def get_billing_stats(self) -> Dict[str, Any]:
        """获取计费统计信息"""
        try:
            # 获取总用户数
            total_users_response = self.supabase.from_("user_profiles").select("user_id", count="exact").execute()
            total_users = total_users_response.count if total_users_response.count else 0
            
            # 获取付费用户数
            premium_users_response = self.supabase.from_("user_subscriptions")\
                .select("user_id", count="exact")\
                .eq("status", "active")\
                .execute()
            premium_users = premium_users_response.count if premium_users_response.count else 0
            
            # 获取免费期用户统计
            free_period_stats = await self._get_free_period_stats()
            
            # 计算转化率
            conversion_rate = (premium_users / total_users * 100) if total_users > 0 else 0
            
            # 获取计费状态
            billing_enabled = await self._is_billing_enabled()
            
            return {
                "success": True,
                "data": {
                    "total_users": total_users,
                    "premium_users": premium_users,
                    "conversion_rate": round(conversion_rate, 2),
                    "billing_enabled": billing_enabled,
                    **free_period_stats
                }
            }
            
        except Exception as e:
            logger.error(f"获取计费统计失败: {e}")
            return {"success": False, "error": str(e)}

    async def _get_free_period_stats(self) -> Dict[str, int]:
        """获取免费期用户统计"""
        try:
            current_time = datetime.now().isoformat()
            
            # 活跃免费期用户
            free_period_response = self.supabase.from_("user_free_periods")\
                .select("period_type", count="exact")\
                .eq("is_active", True)\
                .lte("start_date", current_time)\
                .gte("end_date", current_time)\
                .execute()
            
            stats = {
                "free_period_users": free_period_response.count if free_period_response.count else 0,
                "early_users": 0,
                "trial_users": 0,
                "grace_period_users": 0
            }
            
            # 按类型统计
            if free_period_response.data:
                for item in free_period_response.data:
                    period_type = item.get("period_type", "").lower()
                    if period_type == "early_user":
                        stats["early_users"] += 1
                    elif period_type == "trial":
                        stats["trial_users"] += 1
                    elif period_type == "grace":
                        stats["grace_period_users"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取免费期统计失败: {e}")
            return {
                "free_period_users": 0,
                "early_users": 0,
                "trial_users": 0,
                "grace_period_users": 0
            }