import secrets
import string
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import structlog
from app.services.supabase_client import supabase_service
from app.services.points_service import PointsService

logger = structlog.get_logger()

class ActivationCodeService:
    def __init__(self, access_token: str = None):
        # 激活码服务需要管理员权限，使用service client
        self.supabase = supabase_service.get_client()
        self.points_service = PointsService(access_token)
        self.access_token = access_token
    
    def generate_code(self, length: int = 12) -> str:
        """生成激活码"""
        characters = string.ascii_uppercase + string.digits
        # 排除容易混淆的字符
        characters = characters.replace('0', '').replace('O', '').replace('I', '').replace('1')
        return ''.join(secrets.choice(characters) for _ in range(length))
    
    async def create_activation_codes(
        self, 
        code_type: str,  # credits, subscription
        value: int,
        count: int = 1,
        plan_type: Optional[str] = None,
        description: Optional[str] = None,
        expires_days: int = 365,
        created_by: str = "admin"
    ) -> Dict[str, Any]:
        """批量创建激活码"""
        try:
            batch_id = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            codes_data = []
            generated_codes = []
            
            for _ in range(count):
                # 生成唯一激活码
                while True:
                    code = self.generate_code()
                    # 检查是否重复
                    existing = self.supabase.from_("activation_codes")\
                        .select("id")\
                        .eq("code", code)\
                        .execute()
                    
                    if not existing.data:
                        break
                
                codes_data.append({
                    "code": code,
                    "code_type": code_type,
                    "value": value,
                    "plan_type": plan_type,
                    "description": description or f"{code_type} activation code",
                    "expires_at": expires_at.isoformat(),
                    "created_by": created_by,
                    "batch_id": batch_id
                })
                generated_codes.append(code)
            
            response = self.supabase.from_("activation_codes")\
                .insert(codes_data)\
                .execute()
            
            if response.data:
                logger.info(f"激活码创建成功: 批次{batch_id}, 数量{count}")
                return {
                    "success": True,
                    "batch_id": batch_id,
                    "codes": generated_codes,
                    "count": count,
                    "code_type": code_type,
                    "value": value,
                    "plan_type": plan_type
                }
            
            return {"success": False, "error": "Failed to create activation codes"}
            
        except Exception as e:
            logger.error(f"创建激活码失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def use_activation_code(self, user_id: str, code: str) -> Dict[str, Any]:
        """使用激活码"""
        try:
            # 查找激活码
            response = self.supabase.from_("activation_codes")\
                .select("*")\
                .eq("code", code.upper().strip())\
                .execute()
            
            if not response.data or len(response.data) == 0:
                return {"success": False, "error": "激活码不存在或格式错误"}
            
            activation_code = response.data[0]
            
            # 检查是否已经使用
            if activation_code["is_used"]:
                return {"success": False, "error": "激活码已经被使用过了"}
            
            # 检查是否过期
            if activation_code["expires_at"]:
                from datetime import timezone
                expires_at = datetime.fromisoformat(activation_code["expires_at"].replace('Z', '+00:00'))
                current_time = datetime.now(timezone.utc)
                if current_time > expires_at:
                    return {"success": False, "error": "激活码已过期"}
            
            # 标记为已使用
            update_response = self.supabase.from_("activation_codes")\
                .update({
                    "is_used": True,
                    "used_by": user_id,
                    "used_at": datetime.utcnow().isoformat()
                })\
                .eq("id", activation_code["id"])\
                .execute()
            
            if not update_response.data:
                return {"success": False, "error": "激活码状态更新失败"}
            
            # 根据类型执行相应操作
            code_type = activation_code["code_type"]
            
            # 添加调试日志
            logger.info(f"激活码类型检查: '{code_type}' (type: {type(code_type)})", 
                       activation_code_id=activation_code["id"], 
                       user_id=user_id)
            
            # 标准化类型检查 - 去除空格、引号并转为小写
            code_type_normalized = str(code_type).strip().strip('\'"').lower()
            
            if code_type_normalized == "credits":
                return await self._handle_credits_activation(user_id, activation_code)
            elif code_type_normalized == "subscription":
                return await self._handle_subscription_activation(user_id, activation_code)
            else:
                logger.error(f"未知的激活码类型: '{code_type}' (normalized: '{code_type_normalized}')", 
                           activation_code_id=activation_code["id"])
                return {"success": False, "error": f"未知的激活码类型: '{code_type}'", "message": f"未知的激活码类型: '{code_type}'"}
            
        except Exception as e:
            logger.error(f"使用激活码失败: {e}", user_id=user_id, code=code)
            return {"success": False, "error": str(e)}
    
    async def _handle_credits_activation(self, user_id: str, activation_code: Dict) -> Dict[str, Any]:
        """处理积分激活码"""
        try:
            # 直接操作user_profiles表的积分（与系统其他部分保持一致）
            
            # 1. 获取当前积分
            profile_response = self.supabase.from_("user_profiles")\
                .select("points")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if not profile_response.data:
                return {"success": False, "error": "用户档案不存在"}
            
            current_points = profile_response.data["points"]
            new_points = current_points + activation_code["value"]
            
            # 2. 更新积分
            update_response = self.supabase.from_("user_profiles")\
                .update({"points": new_points})\
                .eq("user_id", user_id)\
                .execute()
            
            if not update_response.data:
                return {"success": False, "error": "积分更新失败"}
            
            logger.info(f"激活码充值成功: 用户{user_id}, 积分 {current_points} -> {new_points}")
            
            # 3. 记录激活码使用日志
            await self._log_activation_code_usage(
                activation_code["id"],
                user_id,
                "credits",
                activation_code["value"],
                None,
                "credits_added",
                {
                    "credits_added": activation_code["value"],
                    "points_before": current_points,
                    "points_after": new_points
                }
            )
            
            return {
                "success": True,
                "type": "credits",
                "value": activation_code["value"],
                "message": f"Successfully recharged {activation_code['value']} credits",
                "points_before": current_points,
                "points_after": new_points
            }
                
        except Exception as e:
            logger.error(f"处理积分激活码失败: {e}", user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _handle_subscription_activation(self, user_id: str, activation_code: Dict) -> Dict[str, Any]:
        """处理订阅激活码"""
        try:
            from app.services.subscription_service import SubscriptionService
            
            plan_type = activation_code["plan_type"]
            logger.info(f"开始处理订阅激活码: plan_type='{plan_type}', value={activation_code['value']}", 
                       activation_code_id=activation_code["id"], 
                       user_id=user_id)
            
            # 验证plan_type
            if not plan_type or plan_type not in ['plus', 'pro', 'max']:
                logger.error(f"无效的订阅计划类型: '{plan_type}'", activation_code_id=activation_code["id"])
                return {"success": False, "error": f"无效的订阅计划类型: '{plan_type}'"}
            
            # 传递access_token确保有足够权限
            subscription_service = SubscriptionService(self.access_token)
            result = await subscription_service.create_subscription(
                user_id, 
                plan_type, 
                payment_method="activation_code"
            )
            
            logger.info(f"订阅服务调用结果: success={result['success']}", 
                       activation_code_id=activation_code["id"], 
                       user_id=user_id, 
                       result=result)
            
            if result["success"]:
                # 确保立即发放积分 - 参考积分激活码的逻辑
                points_result = await self._grant_subscription_points_direct(
                    user_id, 
                    activation_code["plan_type"], 
                    activation_code["value"]
                )
                
                logger.info(f"积分发放结果: {points_result}", 
                           activation_code_id=activation_code["id"], 
                           user_id=user_id)
                
                # 记录激活码使用日志
                await self._log_activation_code_usage(
                    activation_code["id"],
                    user_id,
                    "subscription",
                    activation_code["value"],
                    activation_code["plan_type"],
                    "subscription_" + result["action"],  # subscription_created, subscription_extended, subscription_upgraded
                    {
                        **result["subscription"],
                        "points_granted": points_result
                    }
                )
                
                return {
                    "success": True,
                    "type": "subscription",
                    "plan_type": activation_code["plan_type"],
                    "value": activation_code["value"],
                    "action": result["action"],
                    "message": f"Successfully activated {activation_code['plan_type']} membership",
                    "subscription": result["subscription"],
                    "points_granted": points_result
                }
            else:
                logger.error(f"订阅激活失败: {result.get('error', 'Unknown error')}", 
                           activation_code_id=activation_code["id"], 
                           user_id=user_id)
                return {"success": False, "error": result.get("error", "Subscription activation failed")}
                
        except Exception as e:
            logger.error(f"处理订阅激活码失败: {e}", user_id=user_id)
            return {"success": False, "error": str(e)}
    
    async def _grant_subscription_points_direct(self, user_id: str, plan_type: str, activation_value: int) -> Dict[str, Any]:
        """直接发放订阅积分 - 参考积分激活码的逻辑"""
        try:
            # 获取订阅计划信息
            plan_response = self.supabase.from_("subscription_plans")\
                .select("monthly_credits, duration_days")\
                .eq("plan_type", plan_type)\
                .eq("is_active", True)\
                .single()\
                .execute()
            
            if not plan_response.data:
                logger.error(f"未找到订阅计划: {plan_type}")
                return {"success": False, "error": "Plan not found"}
            
            plan = plan_response.data
            
            # 计算月数（取整）：31天=1个月，90天=3个月
            months = max(1, plan["duration_days"] // 30)  # 至少1个月
            total_points = plan["monthly_credits"] * months
            
            # 1. 获取当前积分 - 使用与积分激活码相同的逻辑
            profile_response = self.supabase.from_("user_profiles")\
                .select("points")\
                .eq("user_id", user_id)\
                .single()\
                .execute()
            
            if not profile_response.data:
                return {"success": False, "error": "用户档案不存在"}
            
            current_points = profile_response.data["points"]
            new_points = current_points + total_points
            
            # 2. 更新积分 - 直接操作user_profiles表确保一致性
            update_response = self.supabase.from_("user_profiles")\
                .update({"points": new_points})\
                .eq("user_id", user_id)\
                .execute()
            
            if not update_response.data:
                return {"success": False, "error": "积分更新失败"}
            
            logger.info(f"订阅激活码积分发放成功: 用户{user_id}, 计划{plan_type}, 积分 {current_points} -> {new_points} (+{total_points}) ({plan['monthly_credits']} × {months}个月)")
            
            return {
                "success": True,
                "points_before": current_points,
                "points_after": new_points,
                "points_added": total_points,
                "plan_monthly_credits": plan["monthly_credits"],
                "duration_days": plan["duration_days"],
                "months_calculated": months
            }
                
        except Exception as e:
            logger.error(f"直接发放订阅积分失败: {e}", user_id=user_id, plan_type=plan_type)
            return {"success": False, "error": str(e)}
    
    async def _log_activation_code_usage(
        self, 
        activation_code_id: str, 
        user_id: str, 
        code_type: str, 
        value: int, 
        plan_type: Optional[str], 
        result_type: str, 
        result_data: Dict[str, Any]
    ):
        """记录激活码使用日志"""
        try:
            log_data = {
                "activation_code_id": activation_code_id,
                "user_id": user_id,
                "code_type": code_type,
                "value": value,
                "plan_type": plan_type,
                "result_type": result_type,
                "result_data": result_data
            }
            
            self.supabase.from_("activation_code_usage_logs")\
                .insert(log_data)\
                .execute()
            
            logger.info(f"激活码使用日志记录成功: {activation_code_id}")
            
        except Exception as e:
            logger.error(f"记录激活码使用日志失败: {e}", activation_code_id=activation_code_id)
    
    async def get_activation_codes(
        self, 
        batch_id: Optional[str] = None,
        code_type: Optional[str] = None,
        is_used: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """获取激活码列表"""
        try:
            query = self.supabase.from_("activation_codes").select("*")
            
            if batch_id:
                query = query.eq("batch_id", batch_id)
            if code_type:
                query = query.eq("code_type", code_type)
            if is_used is not None:
                query = query.eq("is_used", is_used)
            
            # 分页
            offset = (page - 1) * page_size
            query = query.order("created_at", desc=True)\
                        .range(offset, offset + page_size - 1)
            
            response = query.execute()
            
            return {
                "success": True,
                "codes": response.data or [],
                "page": page,
                "page_size": page_size
            }
            
        except Exception as e:
            logger.error(f"获取激活码列表失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_activation_code_stats(self) -> Dict[str, Any]:
        """获取激活码统计信息"""
        try:
            # 获取总体统计
            response = self.supabase.from_("activation_codes")\
                .select("code_type, plan_type, is_used, expires_at")\
                .execute()
            
            if not response.data:
                return {"success": True, "stats": {}}
            
            stats = {}
            for code in response.data:
                key = f"{code['code_type']}_{code.get('plan_type', 'N/A')}"
                if key not in stats:
                    stats[key] = {
                        "code_type": code['code_type'],
                        "plan_type": code.get('plan_type'),
                        "total": 0,
                        "used": 0,
                        "unused": 0,
                        "expired": 0
                    }
                
                stats[key]["total"] += 1
                
                if code["is_used"]:
                    stats[key]["used"] += 1
                else:
                    stats[key]["unused"] += 1
                
                # 检查是否过期
                if code["expires_at"]:
                    from datetime import timezone
                    expires_at = datetime.fromisoformat(code["expires_at"].replace('Z', '+00:00'))
                    current_time = datetime.now(timezone.utc)
                    if current_time > expires_at:
                        stats[key]["expired"] += 1
            
            return {
                "success": True,
                "stats": list(stats.values())
            }
            
        except Exception as e:
            logger.error(f"获取激活码统计失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_activation_history(self, user_id: str) -> Dict[str, Any]:
        """获取用户激活码使用历史"""
        try:
            response = self.supabase.from_("activation_code_usage_logs")\
                .select("*, activation_codes(code, description)")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .execute()
            
            return {
                "success": True,
                "history": response.data or []
            }
            
        except Exception as e:
            logger.error(f"获取用户激活历史失败: {e}", user_id=user_id)
            return {"success": False, "error": str(e)}

# 创建全局激活码服务实例
activation_code_service = ActivationCodeService()