from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import structlog
from app.services.supabase_client import supabase_service
from app.services.points_service import PointsService

logger = structlog.get_logger()

class SubscriptionService:
    def __init__(self, access_token: str = None):
        if access_token:
            self.supabase = supabase_service.get_user_client(access_token)
        else:
            self.supabase = supabase_service.get_client()
        self.points_service = PointsService(access_token)
    
    async def get_user_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户当前最高优先级的有效订阅"""
        try:
            # 使用视图获取当前最高优先级订阅
            response = self.supabase.from_("user_current_subscriptions")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            # 如果视图没有数据，直接查询表
            response = self.supabase.from_("user_subscriptions")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("status", "active")\
                .order("priority", desc=True)\
                .order("end_date", desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
            
        except Exception as e:
            logger.error(f"获取用户订阅失败: {e}", user_id=user_id)
            return None
    
    async def get_subscription_plans(self) -> List[Dict[str, Any]]:
        """获取所有订阅计划"""
        try:
            response = self.supabase.from_("subscription_plans")\
                .select("*")\
                .eq("is_active", True)\
                .order("priority")\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"获取订阅计划失败: {e}")
            return []
    
    async def create_subscription(
        self, 
        user_id: str, 
        plan_type: str, 
        payment_method: str = "activation_code", 
        paid_amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """创建新订阅 - 支持升级和续费逻辑"""
        try:
            # 获取计划信息
            plan_response = self.supabase.from_("subscription_plans")\
                .select("*")\
                .eq("plan_type", plan_type)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if not plan_response.data:
                return {"success": False, "error": "Plan not found"}
            
            plan = plan_response.data
            
            # 获取用户当前订阅
            current_sub = await self.get_user_subscription(user_id)
            
            if current_sub:
                current_plan_priority = current_sub.get("priority", 0)
                new_plan_priority = plan["priority"]
                
                # 同级续费：延长当前订阅
                if current_plan_priority == new_plan_priority:
                    return await self._extend_current_subscription(user_id, current_sub, plan)
                
                # 升级：创建新的高优先级订阅
                elif new_plan_priority > current_plan_priority:
                    return await self._create_upgrade_subscription(user_id, current_sub, plan, payment_method)
                
                # 降级：不允许
                else:
                    return {"success": False, "error": "Downgrade not allowed. Please wait for current subscription to expire."}
            
            else:
                # 新用户或免费用户：直接创建订阅
                return await self._create_new_subscription(user_id, plan, payment_method)
            
        except Exception as e:
            logger.error(f"创建订阅失败: {e}", user_id=user_id, plan_type=plan_type)
            return {"success": False, "error": str(e)}
    
    async def _extend_current_subscription(self, user_id: str, current_sub: Dict, plan: Dict) -> Dict[str, Any]:
        """延长当前订阅"""
        try:
            # 计算新的结束日期
            if current_sub.get("end_date"):
                current_end = datetime.fromisoformat(current_sub["end_date"].replace('Z', '+00:00'))
            else:
                current_end = datetime.utcnow()
            
            new_end_date = current_end + timedelta(days=plan["duration_days"])
            
            # 更新订阅
            response = self.supabase.from_("user_subscriptions")\
                .update({"end_date": new_end_date.isoformat()})\
                .eq("id", current_sub["id"])\
                .execute()
            
            if response.data:
                # 发放积分 - 按续费时长计算总积分
                await self._grant_subscription_points(user_id, plan["monthly_credits"], plan["duration_days"])
                return {"success": True, "action": "extended", "subscription": response.data[0]}
            
            return {"success": False, "error": "Failed to extend subscription"}
            
        except Exception as e:
            logger.error(f"延长订阅失败: {e}", user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _create_upgrade_subscription(self, user_id: str, current_sub: Dict, plan: Dict, payment_method: str) -> Dict[str, Any]:
        """创建升级订阅 - 按比例转换"""
        try:
            # 计算当前订阅剩余价值
            upgrade_calculation = await self._calculate_upgrade_cost(current_sub, plan)
            
            if not upgrade_calculation["can_upgrade"]:
                return {"success": False, "error": upgrade_calculation["error"]}
            
            # 按比例转换：根据剩余价值计算新订阅时长
            converted_days = upgrade_calculation["converted_days"]
            end_date = datetime.utcnow() + timedelta(days=converted_days)
            
            # 标记旧订阅为已升级
            self.supabase.from_("user_subscriptions")\
                .update({"status": "upgraded"})\
                .eq("id", current_sub["id"])\
                .execute()
            
            # 创建新的升级订阅
            subscription_data = {
                "user_id": user_id,
                "plan_type": plan["plan_type"],
                "plan_name": plan["plan_name"],
                "status": "active",
                "end_date": end_date.isoformat(),
                "payment_method": payment_method,
                "amount": 0,  # 按比例转换无需额外付费
                "original_amount": plan["price"],
                "monthly_credits": plan["monthly_credits"],
                "priority": plan["priority"],
                "source_subscription_id": current_sub["id"],
                "upgrade_credit_used": upgrade_calculation["credit_used"],
                "last_credits_grant_date": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.from_("user_subscriptions")\
                .insert(subscription_data)\
                .execute()
            
            if response.data:
                # 发放积分 - 升级时发放完整的新计划积分
                await self._grant_subscription_points(user_id, plan["monthly_credits"], plan["duration_days"])
                return {
                    "success": True, 
                    "action": "upgraded", 
                    "subscription": response.data[0],
                    "upgrade_details": upgrade_calculation
                }
            
            return {"success": False, "error": "Failed to create upgrade subscription"}
            
        except Exception as e:
            logger.error(f"创建升级订阅失败: {e}", user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _create_new_subscription(self, user_id: str, plan: Dict, payment_method: str) -> Dict[str, Any]:
        """创建新订阅"""
        try:
            # 计算结束日期
            end_date = datetime.utcnow() + timedelta(days=plan["duration_days"])
            
            # 创建订阅记录
            subscription_data = {
                "user_id": user_id,
                "plan_type": plan["plan_type"],
                "plan_name": plan["plan_name"],
                "status": "active",
                "end_date": end_date.isoformat(),
                "payment_method": payment_method,
                "amount": plan["price"],
                "monthly_credits": plan["monthly_credits"],
                "priority": plan["priority"],
                "last_credits_grant_date": datetime.utcnow().isoformat()
            }
            
            response = self.supabase.from_("user_subscriptions")\
                .insert(subscription_data)\
                .execute()
            
            if response.data:
                # 立即发放积分 - 按订阅时长计算总积分
                await self._grant_subscription_points(user_id, plan["monthly_credits"], plan["duration_days"])
                return {"success": True, "action": "created", "subscription": response.data[0]}
            
            return {"success": False, "error": "Failed to create subscription"}
            
        except Exception as e:
            logger.error(f"创建新订阅失败: {e}", user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _calculate_upgrade_cost(self, current_sub: Dict, new_plan: Dict) -> Dict[str, Any]:
        """计算升级成本，按比例转换"""
        try:
            # 获取当前订阅的计划信息
            current_plan_response = self.supabase.from_("subscription_plans")\
                .select("*")\
                .eq("plan_type", current_sub["plan_type"])\
                .single()\
                .execute()
            
            if not current_plan_response.data:
                return {"can_upgrade": False, "error": "Current plan not found"}
            
            current_plan = current_plan_response.data
            
            # 计算剩余天数
            if current_sub.get("end_date"):
                current_end = datetime.fromisoformat(current_sub["end_date"].replace('Z', '+00:00'))
                remaining_days = (current_end - datetime.utcnow()).days
            else:
                remaining_days = 0
            
            if remaining_days <= 0:
                return {"can_upgrade": False, "error": "Current subscription has expired"}
            
            # 计算剩余价值
            total_days = current_plan["duration_days"]
            daily_rate_current = current_plan["price"] / total_days if total_days > 0 else 0
            daily_rate_new = new_plan["price"] / new_plan["duration_days"] if new_plan["duration_days"] > 0 else 0
            
            remaining_value = remaining_days * daily_rate_current
            
            # 按比例转换为新订阅天数
            if daily_rate_new > 0:
                converted_days = int(remaining_value / daily_rate_new)
            else:
                converted_days = 0
            
            return {
                "can_upgrade": True,
                "remaining_days": remaining_days,
                "remaining_value": round(remaining_value, 2),
                "credit_used": round(remaining_value, 2),
                "converted_days": converted_days,
                "daily_rate_current": round(daily_rate_current, 2),
                "daily_rate_new": round(daily_rate_new, 2)
            }
            
        except Exception as e:
            logger.error(f"计算升级成本失败: {e}")
            return {"can_upgrade": False, "error": str(e)}
    
    async def _grant_subscription_points(self, user_id: str, monthly_credits: int, duration_days: int = 30):
        """发放订阅积分 - 按月数倍增，但每月固定积分"""
        try:
            # 计算月数（取整）：31天=1个月，90天=3个月
            months = max(1, duration_days // 30)  # 至少1个月
            total_points = monthly_credits * months
            
            from app.schemas.points import RechargePointsRequest
            
            request = RechargePointsRequest(
                points_to_add=total_points,
                description=f"Subscription membership points grant ({monthly_credits} × {months} months = {total_points} points for {duration_days} days)",
                request_id=f"subscription_grant_{user_id}_{datetime.utcnow().timestamp()}"
            )
            
            result = await self.points_service.recharge_points(user_id, request)
            if result.success:
                logger.info(f"订阅积分发放成功: {user_id}, 积分: {total_points} ({monthly_credits} × {months}个月, {duration_days}天)")
            else:
                logger.error(f"订阅积分发放失败: {user_id}, 积分: {total_points}")
            
        except Exception as e:
            logger.error(f"订阅积分发放失败: {e}", user_id=user_id, points=total_points)
    
    async def update_subscription_from_revenuecat(
        self, 
        user_id: str, 
        subscription_info: Dict[str, Any], 
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """从 RevenueCat 数据更新用户订阅状态"""
        try:
            status = subscription_info.get("status", "inactive")
            active_entitlements = subscription_info.get("active_entitlements", [])
            is_trial = subscription_info.get("is_trial", False)
            expiry_date = subscription_info.get("expiry_date")
            
            logger.info(
                "Updating subscription from RevenueCat",
                user_id=user_id,
                status=status,
                entitlements=active_entitlements,
                is_trial=is_trial
            )
            
            if status == "active" and "premium" in active_entitlements:
                # 用户有活跃的高级订阅
                plan_type = "trial" if is_trial else "monthly"  # 根据需要调整
                
                # 查找或创建对应的订阅计划
                plan = await self._get_or_create_revenuecat_plan(plan_type, is_trial)
                if not plan:
                    logger.error("Failed to get RevenueCat plan", plan_type=plan_type)
                    return {"success": False, "error": "Plan not found"}
                
                # 检查用户是否已有活跃订阅
                current_sub = await self.get_user_subscription(user_id)
                
                if current_sub and current_sub.get("status") == "active":
                    # 更新现有订阅
                    update_data = {
                        "status": "active",
                        "payment_method": "revenuecat",
                        "transaction_id": transaction_id
                    }
                    
                    if expiry_date:
                        update_data["end_date"] = expiry_date
                    
                    response = self.supabase.from_("user_subscriptions")\
                        .update(update_data)\
                        .eq("id", current_sub["id"])\
                        .execute()
                    
                    logger.info("Updated existing subscription from RevenueCat", user_id=user_id)
                else:
                    # 创建新订阅
                    end_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00')) if expiry_date else (datetime.utcnow() + timedelta(days=30))
                    
                    subscription_data = {
                        "user_id": user_id,
                        "plan_type": plan["plan_type"],
                        "plan_name": plan["plan_name"],
                        "status": "active",
                        "end_date": end_date.isoformat(),
                        "payment_method": "revenuecat",
                        "transaction_id": transaction_id,
                        "amount": plan["price"],
                        "monthly_credits": plan["monthly_credits"],
                        "priority": plan["priority"]
                    }
                    
                    response = self.supabase.from_("user_subscriptions")\
                        .insert(subscription_data)\
                        .execute()
                    
                    if response.data:
                        # 发放订阅积分
                        duration_days = (end_date - datetime.utcnow()).days
                        await self._grant_subscription_points(user_id, plan["monthly_credits"], duration_days)
                    
                    logger.info("Created new subscription from RevenueCat", user_id=user_id)
                
                return {"success": True, "action": "updated", "status": "active"}
            
            else:
                # 订阅不活跃，取消现有订阅
                response = self.supabase.from_("user_subscriptions")\
                    .update({"status": "cancelled"})\
                    .eq("user_id", user_id)\
                    .eq("status", "active")\
                    .execute()
                
                logger.info("Cancelled subscription from RevenueCat", user_id=user_id)
                return {"success": True, "action": "cancelled", "status": "inactive"}
            
        except Exception as e:
            logger.error("Error updating subscription from RevenueCat", error=str(e), user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _get_or_create_revenuecat_plan(self, plan_type: str, is_trial: bool) -> Optional[Dict[str, Any]]:
        """获取或创建 RevenueCat 对应的订阅计划"""
        try:
            # 首先尝试查找现有计划
            response = self.supabase.from_("subscription_plans")\
                .select("*")\
                .eq("plan_type", plan_type)\
                .eq("is_active", True)\
                .execute()
            
            if response.data:
                return response.data[0]
            
            # 如果没有找到，创建默认计划
            default_plan = {
                "plan_type": plan_type,
                "plan_name": "RevenueCat Trial" if is_trial else "RevenueCat Premium",
                "price": 0 if is_trial else 999,  # 试用版免费，付费版默认9.99
                "duration_days": 7 if is_trial else 30,
                "monthly_credits": 5000 if is_trial else 10000,
                "priority": 1 if is_trial else 5,
                "is_active": True,
                "features": ["ai_assistance", "premium_features"],
                "description": "RevenueCat managed subscription"
            }
            
            response = self.supabase.from_("subscription_plans")\
                .insert(default_plan)\
                .execute()
            
            if response.data:
                logger.info("Created RevenueCat plan", plan_type=plan_type, is_trial=is_trial)
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error("Error getting/creating RevenueCat plan", error=str(e))
            return None

# 创建全局订阅服务实例
subscription_service = SubscriptionService()