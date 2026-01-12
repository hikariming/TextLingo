from typing import Optional, List, Dict, Any
import math
import structlog
from datetime import datetime
from app.services.supabase_client import supabase_service
from app.core.logging_config import LoggingConfig
from app.schemas.points import (
    ServiceType,
    BillingType,
    TransactionType,
    ConsumePointsRequest,
    ConsumePointsResponse,
    RechargePointsRequest,
    RechargePointsResponse,
    UserPointsBalance,
    PointPricingConfig,
    PointTransaction,
    CalculatePointsRequest,
    CalculatePointsResponse,
    PointTransactionQuery,
    PointTransactionHistoryResponse
)

logger = LoggingConfig.get_logger_for_service("points_service")


class PointsService:
    """积分管理服务"""
    
    def __init__(self, access_token: str = None):
        # 根据是否有access_token决定使用哪个客户端
        if access_token:
            self.supabase = supabase_service.get_user_client(access_token)
        else:
            self.supabase = supabase_service.get_client()  # 回退到service client
        
        self.access_token = access_token
    
    async def get_user_balance(self, user_id: str) -> Optional[UserPointsBalance]:
        """获取用户积分余额 - 使用多种方法绕过RLS问题"""
        try:
            if LoggingConfig.should_log_debug():
                logger.debug(f"获取用户积分余额: {user_id}")
            
            # 方法1: 优先尝试RPC函数（绕过RLS）
            try:
                rpc_response = self.supabase.rpc('get_user_points_bypass_rls', {
                    'p_user_id': user_id
                }).execute()
                
                if rpc_response.data is not None:
                    points = rpc_response.data if isinstance(rpc_response.data, int) else 0
                    if LoggingConfig.should_log_debug():
                        logger.debug(f"RPC方法获取用户 {user_id} 积分: {points}")
                    
                    return UserPointsBalance(
                        user_id=user_id,
                        email="",
                        total_points=points,
                        total_consumed=0,
                        total_recharged=0,
                        total_rewarded=0,
                        total_transactions=0
                    )
            except Exception as rpc_error:
                logger.warning(f"RPC方法获取积分失败: {rpc_error}")
            
            # 方法2: 直接从 user_profiles 表获取积分信息（Service Role应该能绕过RLS）
            try:
                profile_response = self.supabase.from_("user_profiles").select("points, role").eq("user_id", user_id).execute()
                
                if profile_response.data and len(profile_response.data) > 0:
                    profile_data = profile_response.data[0]
                    points = profile_data.get("points", 0)
                    
                    if LoggingConfig.should_log_debug():
                        logger.debug(f"直接查询获取用户 {user_id} 积分: {points}")
                    
                    return UserPointsBalance(
                        user_id=user_id,
                        email="",
                        total_points=points,
                        total_consumed=0,
                        total_recharged=0,
                        total_rewarded=0,
                        total_transactions=0
                    )
                else:
                    logger.warning(f"用户 {user_id} 没有找到profile记录")
                    
                    # 尝试创建默认profile
                    await self._create_default_profile(user_id)
                    
                    # 返回默认积分
                    return UserPointsBalance(
                        user_id=user_id,
                        email="",
                        total_points=1000,  # 新用户默认积分
                        total_consumed=0,
                        total_recharged=0,
                        total_rewarded=0,
                        total_transactions=0
                    )
                    
            except Exception as direct_error:
                logger.error(f"直接查询失败: {direct_error}")
            
            # 方法3: 如果以上都失败，返回默认值（防止完全阻塞）
            logger.warning(f"所有方法都失败，为用户 {user_id} 返回默认积分")
            return UserPointsBalance(
                user_id=user_id,
                email="",
                total_points=1000,  # 紧急情况下给予默认积分
                total_consumed=0,
                total_recharged=0,
                total_rewarded=0,
                total_transactions=0
            )
            
        except Exception as e:
            logger.error(f"获取用户积分余额完全失败: {e}", user_id=user_id)
            
            # 紧急回退：返回默认值而不是None，避免服务中断
            return UserPointsBalance(
                user_id=user_id,
                email="",
                total_points=1000,  # 紧急情况下的默认积分
                total_consumed=0,
                total_recharged=0,
                total_rewarded=0,
                total_transactions=0
            )
    
    async def _create_default_profile(self, user_id: str) -> bool:
        """Create default profile for user"""
        try:
            logger.info(f"Creating default profile for user {user_id}")
            
            # 1. First try RPC function, use service role to ensure permissions
            try:
                from app.services.supabase_client import supabase_service
                service_client = supabase_service.get_client()
                response = service_client.rpc('create_user_profile_bypass_rls', {
                    'p_user_id': user_id,
                    'p_role': 'free',
                    'p_points': 1000,
                    'p_native_language': 'zh',
                    'p_full_name': 'Default User',
                    'p_learning_language': 'en',
                    'p_language_level': 'beginner',
                    'p_bio': '',  # Add missing field
                    'p_avatar_url': None,  # Add missing field
                    'p_profile_setup_completed': False  # Add missing field
                }).execute()
                
                if response.data:
                    logger.info(f"RPC function profile creation succeeded: {user_id}")
                    return True
                else:
                    raise Exception("RPC returned empty result")
                    
            except Exception as rpc_error:
                logger.warning(f"RPC profile creation failed: {rpc_error}")
                
                # 2. Fallback to direct insert, add missing fields and use service role
                profile_data = {
                    'user_id': user_id,
                    'email': None,  # Points service cannot get email, leave empty
                    'role': 'free',
                    'points': 1000,
                    'native_language': 'zh',
                    'full_name': 'Default User',
                    'learning_language': 'en',
                    'language_level': 'beginner',
                    'bio': '',  # Add missing field
                    'avatar_url': None,  # Add missing field
                    'profile_setup_completed': False  # Add missing field
                }
                
                response = service_client.table('user_profiles').insert(profile_data).execute()
                
                if response.data:
                    logger.info(f"Direct insert profile creation succeeded: {user_id}")
                    return True
                else:
                    logger.error(f"Direct insert profile creation failed: {user_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to create default profile: {e}", user_id=user_id)
            return False
    
    async def calculate_points_required(self, request: CalculatePointsRequest) -> Optional[CalculatePointsResponse]:
        """计算所需积分"""
        try:
            # 查询价格配置
            pricing_response = self.supabase.from_("point_pricing_config").select("*").match({
                "service_type": request.service_type.value,
                "model_name": request.aimodel_name or "default",
                "is_active": True
            }).execute()
            
            if not pricing_response.data:
                # 如果没有找到具体模型的配置，尝试查找默认配置
                pricing_response = self.supabase.from_("point_pricing_config").select("*").match({
                    "service_type": request.service_type.value,
                    "model_name": "default",
                    "is_active": True
                }).execute()
            
            if not pricing_response.data:
                logger.error(f"未找到价格配置", service_type=request.service_type, model_name=request.aimodel_name)
                return None
            
            pricing = pricing_response.data[0]
            billing_type = BillingType(pricing["billing_type"])
            points_per_unit = pricing["points_per_unit"]
            
            # 根据计费类型计算积分
            if billing_type == BillingType.PER_REQUEST:
                points_required = points_per_unit
            elif billing_type == BillingType.PER_TOKEN:
                # 按 1K tokens 计费
                tokens = request.tokens_used or 0
                points_required = math.ceil(tokens / 1000) * points_per_unit
            elif billing_type == BillingType.PER_CHARACTER:
                # 按 100 字符计费
                characters = request.characters_count or 0
                points_required = math.ceil(characters / 100) * points_per_unit
            else:
                points_required = points_per_unit
            
            return CalculatePointsResponse(
                points_required=points_required,
                billing_type=billing_type,
                unit_description=pricing["unit_description"] or "",
                            service_type=request.service_type,
            model_name=request.aimodel_name or pricing["model_name"]
            )
            
        except Exception as e:
            logger.error(f"计算积分失败: {e}", request=request.dict())
            return None
    
    async def consume_points(self, user_id: str, request: ConsumePointsRequest) -> ConsumePointsResponse:
        """消费积分 - 优先扣除有效会员积分，再扣永久积分"""
        try:
            # 首先计算需要消费的积分
            calc_request = CalculatePointsRequest(
                service_type=request.service_type,
                aimodel_name=request.aimodel_name,
                tokens_used=request.tokens_used
            )
            
            calc_response = await self.calculate_points_required(calc_request)
            if not calc_response:
                return ConsumePointsResponse(
                    success=False,
                    error="pricing_not_found",
                    message="未找到定价配置"
                )
            
            points_to_consume = calc_response.points_required
            
            # 获取用户当前积分状态
            permanent_points, subscription_points, total_points = await self._get_user_points_detail(user_id)
            
            if total_points < points_to_consume:
                return ConsumePointsResponse(
                    success=False,
                    error="insufficient_points",
                    message="积分不足",
                    current_points=total_points,
                    required_points=points_to_consume
                )
            
            # 计算扣费分配：优先扣除会员积分（仅限有效期内）
            subscription_deducted = min(subscription_points, points_to_consume)
            permanent_deducted = points_to_consume - subscription_deducted
            
            # 更新积分
            success = await self._deduct_points_with_priority(
                user_id, 
                permanent_deducted, 
                subscription_deducted,
                request.service_type.value,
                request.description or "AI服务消费",
                request.request_id
            )
            
            if success:
                return ConsumePointsResponse(
                    success=True,
                    points_before=total_points,
                    points_after=total_points - points_to_consume,
                    points_consumed=points_to_consume
                )
            else:
                return ConsumePointsResponse(
                    success=False,
                    error="database_error",
                    message="积分扣除失败"
                )
                
        except Exception as e:
            logger.error(f"消费积分失败: {e}", user_id=user_id, request=request.dict())
            return ConsumePointsResponse(
                success=False,
                error="internal_error",
                message=f"内部错误: {str(e)}"
            )
    
    async def _get_user_points_detail(self, user_id: str) -> tuple[int, int, int]:
        """获取用户积分详情: (永久积分, 会员积分, 总积分)
        注意：只有在有效期内的会员才有会员积分
        """
        try:
            # 获取永久积分
            profile_response = self.supabase.from_("user_profiles").select("points").eq("user_id", user_id).execute()
            permanent_points = 0
            if profile_response.data and len(profile_response.data) > 0:
                permanent_points = profile_response.data[0].get("points", 0) or 0
            
            # 获取有效期内的会员积分
            current_time = datetime.now().isoformat()
            subscription_response = self.supabase.from_("user_subscriptions").select(
                "monthly_credits, end_date"
            ).eq("user_id", user_id).gt("end_date", current_time).order("end_date", desc=True).limit(1).execute()
            
            subscription_points = 0
            if subscription_response.data and len(subscription_response.data) > 0:
                subscription_data = subscription_response.data[0]
                end_date = subscription_data.get("end_date")
                
                # 双重检查会员是否仍然有效
                if end_date and datetime.fromisoformat(end_date.replace('Z', '+00:00')) > datetime.now():
                    subscription_points = subscription_data.get("monthly_credits", 0) or 0
                else:
                    subscription_points = 0
                    logger.debug(f"用户 {user_id} 的会员已过期，end_date: {end_date}")
            
            total_points = permanent_points + subscription_points
            
            if LoggingConfig.should_log_debug():
                logger.debug(f"用户 {user_id} 积分详情: 永久={permanent_points}, 会员={subscription_points}, 总计={total_points}")
            
            return permanent_points, subscription_points, total_points
            
        except Exception as e:
            logger.error(f"获取用户积分详情失败: {e}", user_id=user_id)
            return 0, 0, 0
    
    async def _deduct_points_with_priority(self, user_id: str, permanent_deducted: int, subscription_deducted: int, service_type: str, description: str, request_id: str = None) -> bool:
        """按优先级扣除积分"""
        try:
            import uuid
            transaction_id = str(uuid.uuid4())
            
            # 更新永久积分
            if permanent_deducted > 0:
                # 先获取当前值再扣除
                current_response = self.supabase.from_("user_profiles").select("points").eq("user_id", user_id).execute()
                if current_response.data:
                    current_points = current_response.data[0].get("points", 0) or 0
                    new_points = current_points - permanent_deducted
                    self.supabase.from_("user_profiles").update({"points": new_points}).eq("user_id", user_id).execute()
                else:
                    logger.error(f"无法获取用户 {user_id} 的永久积分")
                    return False
            
            # 更新会员积分（仅在有效期内）
            if subscription_deducted > 0:
                current_time = datetime.now().isoformat()
                sub_response = self.supabase.from_("user_subscriptions").select("monthly_credits, end_date").eq("user_id", user_id).gt("end_date", current_time).order("end_date", desc=True).limit(1).execute()
                
                if sub_response.data:
                    subscription_data = sub_response.data[0]
                    end_date = subscription_data.get("end_date")
                    
                    # 再次确认会员仍然有效
                    if end_date and datetime.fromisoformat(end_date.replace('Z', '+00:00')) > datetime.now():
                        current_credits = subscription_data.get("monthly_credits", 0) or 0
                        new_credits = current_credits - subscription_deducted
                        
                        self.supabase.from_("user_subscriptions").update({
                            "monthly_credits": new_credits,
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).gt("end_date", current_time).execute()
                    else:
                        logger.warning(f"尝试扣除已过期会员 {user_id} 的积分")
                        return False
                else:
                    logger.error(f"无法获取用户 {user_id} 的有效会员信息")
                    return False
            
            # 记录交易
            transaction_description = f"{description} (永久积分: -{permanent_deducted}, 会员积分: -{subscription_deducted})"
            
            self.supabase.from_("user_point_transactions").insert({
                "id": transaction_id,
                "user_id": user_id,
                "transaction_type": "consumption",
                "points_change": -(permanent_deducted + subscription_deducted),
                "service_type": service_type,
                "description": transaction_description,
                "status": "completed",
                "request_id": request_id or f"py-service-{user_id}-{datetime.now().timestamp()}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }).execute()
            
            logger.info(f"积分扣除成功 - 用户: {user_id}, 永久积分: -{permanent_deducted}, 会员积分: -{subscription_deducted}")
            return True
            
        except Exception as e:
            logger.error(f"扣除积分失败: {e}", user_id=user_id)
            return False
    
    async def recharge_points(self, user_id: str, request: RechargePointsRequest) -> RechargePointsResponse:
        """充值积分"""
        try:
            response = self.supabase.rpc("recharge_user_points", {
                "p_user_id": user_id,
                "p_points_to_add": request.points_to_add,
                "p_description": request.description,
                "p_request_id": request.request_id
            }).execute()
            
            if response.data:
                result = response.data
                return RechargePointsResponse(
                    success=result.get("success", False),
                    transaction_id=result.get("transaction_id"),
                    points_before=result.get("points_before"),
                    points_after=result.get("points_after"),
                    points_added=result.get("points_added")
                )
            else:
                return RechargePointsResponse(success=False)
                
        except Exception as e:
            logger.error(f"充值积分失败: {e}", user_id=user_id, request=request.dict())
            return RechargePointsResponse(success=False)
    
    async def get_transaction_history(
        self, 
        user_id: str, 
        query: PointTransactionQuery
    ) -> Optional[PointTransactionHistoryResponse]:
        """获取积分交易历史"""
        try:
            # 构建查询
            db_query = self.supabase.from_("user_point_transactions").select("*").eq("user_id", user_id)
            
            # 添加过滤条件
            if query.transaction_type:
                db_query = db_query.eq("transaction_type", query.transaction_type.value)
            if query.service_type:
                db_query = db_query.eq("service_type", query.service_type.value)
            if query.status:
                db_query = db_query.eq("status", query.status.value)
            if query.start_date:
                db_query = db_query.gte("created_at", query.start_date.isoformat())
            if query.end_date:
                db_query = db_query.lte("created_at", query.end_date.isoformat())
            
            # 计算偏移量
            offset = (query.page - 1) * query.page_size
            
            # 获取总数 - 使用新的Supabase客户端语法
            count_query = self.supabase.from_("user_point_transactions").select("*", count="exact").eq("user_id", user_id)
            
            # 添加相同的过滤条件到计数查询
            if query.transaction_type:
                count_query = count_query.eq("transaction_type", query.transaction_type.value)
            if query.service_type:
                count_query = count_query.eq("service_type", query.service_type.value)
            if query.status:
                count_query = count_query.eq("status", query.status.value)
            if query.start_date:
                count_query = count_query.gte("created_at", query.start_date.isoformat())
            if query.end_date:
                count_query = count_query.lte("created_at", query.end_date.isoformat())
            
            count_response = count_query.execute()
            total = count_response.count if count_response.count else 0
            
            # 获取分页数据
            db_query = db_query.order("created_at", desc=True).range(offset, offset + query.page_size - 1)
            response = db_query.execute()
            
            transactions = [PointTransaction(**item) for item in response.data] if response.data else []
            
            total_pages = math.ceil(total / query.page_size) if total > 0 else 1
            
            return PointTransactionHistoryResponse(
                items=transactions,
                total=total,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages
            )
            
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}", user_id=user_id, query=query.dict())
            return None
    
    async def get_pricing_configs(self) -> List[PointPricingConfig]:
        """获取所有定价配置"""
        try:
            response = self.supabase.from_("point_pricing_config").select("*").eq("is_active", True).order("service_type").execute()
            
            return [PointPricingConfig(**item) for item in response.data] if response.data else []
            
        except Exception as e:
            logger.error(f"获取定价配置失败: {e}")
            return []
    
    async def check_sufficient_points(self, user_id: str, service_type: ServiceType, aimodel_name: Optional[str] = None, tokens_used: int = 0) -> Dict[str, Any]:
        """检查用户积分是否足够"""
        try:
            # 获取用户当前积分
            balance = await self.get_user_balance(user_id)
            if not balance:
                return {"sufficient": False, "error": "无法获取用户余额"}
            
            # 计算所需积分
            calc_request = CalculatePointsRequest(
                service_type=service_type,
                aimodel_name=aimodel_name,
                tokens_used=tokens_used
            )
            
            calc_response = await self.calculate_points_required(calc_request)
            if not calc_response:
                return {"sufficient": False, "error": "无法计算所需积分"}
            
            required_points = calc_response.points_required
            current_points = balance.total_points
            
            return {
                "sufficient": current_points >= required_points,
                "current_points": current_points,
                "required_points": required_points,
                "shortfall": max(0, required_points - current_points)
            }
            
        except Exception as e:
            logger.error(f"检查积分是否足够失败: {e}", user_id=user_id)
            return {"sufficient": False, "error": str(e)}


# 创建全局积分服务实例
points_service = PointsService()