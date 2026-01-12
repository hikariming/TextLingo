"""
Dify 通用助手服务 - 支持多模型选择的聊天功能
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any, Optional, List
import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.dify_config import dify_config
from app.services.points_service import PointsService
from app.services.supabase_client import supabase_service
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class DifyUniversalService:
    """Dify 通用助手服务"""
    
    def __init__(self):
        """初始化通用助手服务"""
        # 获取通用助手流配置
        self.flow_config = dify_config.get_flow("universal-assistant")
        if not self.flow_config:
            raise HTTPException(
                status_code=500,
                detail="未找到通用助手配置"
            )
        
        self.api_url = self.flow_config.api_url
        self.api_token = self.flow_config.api_token
        self.flow_id = self.flow_config.id
        
        # 获取支持的模型配置
        self.supported_models = {
            model.id: model for model in self.flow_config.supported_models
        }
        
        try:
            self.points_service = PointsService()
            logger.info("积分服务初始化成功")
        except Exception as e:
            logger.error(f"初始化积分服务失败: {e}", exc_info=True)
            self.points_service = None
    
    async def validate_model_access(self, user_id: str, model_id: str) -> None:
        """
        验证用户是否有权限使用指定模型
        
        Args:
            user_id: 用户ID
            model_id: 模型ID
        """
        # 检查模型是否存在
        if model_id not in self.supported_models:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型: {model_id}"
            )
        
        model_config = self.supported_models[model_id]
        
        # 检查模型是否激活
        if not model_config.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"模型 {model_id} 当前不可用"
            )
        
        # 检查用户会员等级权限
        if model_config.required_tier != "free":
            try:
                user_service = UserService()
                profile = await user_service.get_user_profile(user_id)
                
                if not profile:
                    raise HTTPException(
                        status_code=403,
                        detail="用户资料不存在，无法验证模型权限"
                    )
                
                user_tier = profile.get("tier", "free")
                required_tier = model_config.required_tier
                
                # 简单的等级检查逻辑
                tier_hierarchy = {"free": 0, "plus": 1, "pro": 2, "max": 3}
                user_level = tier_hierarchy.get(user_tier, 0)
                required_level = tier_hierarchy.get(required_tier, 0)
                
                if user_level < required_level:
                    raise HTTPException(
                        status_code=403,
                        detail=f"您的会员等级（{user_tier}）不足，无法使用模型 {model_config.name}，需要 {required_tier} 等级"
                    )
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"验证用户模型权限时出错: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="权限验证失败"
                )
    
    def calculate_model_points(self, model_id: str, usage_data: Dict[str, Any]) -> int:
        """
        根据模型和使用量计算积分消耗（包含保底消费机制）
        注意：此方法只在成功获得API响应时调用，确保保底消费只针对正常服务
        
        Args:
            model_id: 模型ID
            usage_data: 使用量数据 (包含 prompt_tokens, completion_tokens 等)
            
        Returns:
            计算的积分数量（包含保底消费）
        """
        if model_id not in self.supported_models:
            return 30  # 默认积分
        
        model_config = self.supported_models[model_id]
        billing_settings = dify_config.config.get("billing_settings", {})
        min_points_charge = billing_settings.get("min_points_charge", 1)
        
        # 优先使用 total_price 计算（如果有的话）
        if "total_price" in usage_data and usage_data["total_price"]:
            try:
                total_price = float(usage_data["total_price"])
                # 根据配置文件中的汇率计算积分
                usd_to_points = dify_config.config.get("token_rate_mapping", {}).get("usd_to_points", 1000)
                points = int(total_price * usd_to_points)
                # 应用保底消费：至少收取模型基础费用
                return max(points, model_config.base_cost, min_points_charge)
            except (ValueError, TypeError):
                pass
        
        # 回退到基于 token 的计算
        try:
            prompt_tokens = int(usage_data.get("prompt_tokens", 0))
            completion_tokens = int(usage_data.get("completion_tokens", 0))
            
            # 计算token成本（每1000个token）
            prompt_cost = (prompt_tokens * model_config.input_token_cost) / 1000
            completion_cost = (completion_tokens * model_config.output_token_cost) / 1000
            base_cost = model_config.base_cost
            
            # 基于实际使用量的积分计算
            usage_based_points = int(prompt_cost + completion_cost)
            
            # 应用保底消费机制：实际消费 = max(使用量计算, 基础费用, 最小费用)
            total_points = max(usage_based_points + base_cost, base_cost, min_points_charge)
            
            logger.info(f"模型 {model_id} 积分计算: 使用量{usage_based_points} + 基础{base_cost} = {total_points} (保底:{min_points_charge})")
            return total_points
            
        except (ValueError, TypeError) as e:
            logger.warning(f"计算积分时出错: {e}，使用模型基础积分")
            # 确保即使出错也有保底消费
            return max(model_config.base_cost, min_points_charge)
    
    async def deduct_points_for_model(self, user_id: str, model_id: str) -> tuple[bool, int, int]:
        """
        为指定模型预扣积分
        
        Args:
            user_id: 用户ID
            model_id: 模型ID
            
        Returns:
            (是否扣除成功, 扣除前的积分, 预扣积分数量)
        """
        if not self.points_service:
            logger.warning("积分服务不可用，跳过积分检查")
            return False, 0, 0
        
        model_config = self.supported_models.get(model_id)
        if not model_config:
            raise HTTPException(status_code=400, detail=f"未知模型: {model_id}")
        
        # 预估积分（使用基础费用 + 预扣倍数）
        base_cost = model_config.base_cost
        pre_charge_multiplier = dify_config.config.get("billing_settings", {}).get("pre_charge_multiplier", 1.2)
        estimated_points = max(int(base_cost * pre_charge_multiplier), base_cost)
        
        try:
            # 获取用户当前积分
            balance = await self.points_service.get_user_balance(user_id)
            if not balance:
                logger.warning(f"用户 {user_id} 积分余额获取失败，可能需要创建资料")
                try:
                    user_service = UserService()
                    profile = await user_service.get_user_profile(user_id)
                    if profile:
                        logger.info(f"为用户 {user_id} 确认了个人资料")
                    return False, 0, 0  # 本次免积分
                except Exception as e:
                    logger.error(f"为用户 {user_id} 创建资料失败: {e}")
                    return False, 0, 0
            
            if balance.total_points < estimated_points:
                raise HTTPException(
                    status_code=402,
                    detail=f"积分不足，当前积分: {balance.total_points}，预估需要: {estimated_points}"
                )
            
            points_before = balance.total_points
            new_points = points_before - estimated_points
            
            # 扣除积分
            supabase = supabase_service.get_client()
            try:
                # 优先使用RPC函数
                rpc_result = supabase.rpc('update_user_points_bypass_rls', {
                    'p_user_id': user_id,
                    'p_new_points': new_points
                }).execute()
                
                if rpc_result.data:
                    logger.info(f"模型 {model_id} 预扣 {estimated_points} 积分成功 (基础:{base_cost}, 倍数:{pre_charge_multiplier})，剩余: {new_points}")
                    return True, points_before, estimated_points
                else:
                    raise Exception("RPC更新积分失败")
                    
            except Exception as rpc_error:
                logger.warning(f"RPC方法更新积分失败: {rpc_error}，尝试直接更新")
                
                update_result = supabase.from_("user_profiles").update({
                    "points": new_points
                }).eq("user_id", user_id).execute()
                
                if update_result.data:
                    logger.info(f"模型 {model_id} 直接更新预扣 {estimated_points} 积分成功")
                    return True, points_before, estimated_points
                else:
                    raise HTTPException(status_code=500, detail="积分扣除失败")
                    
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"积分扣除异常: {e}")
            raise HTTPException(status_code=500, detail=f"积分扣除失败: {str(e)}")
    
    async def refund_points(self, user_id: str, points_before: int, reason: str = "API调用失败"):
        """
        退还积分（出错时全额退费，不收保底费用）
        
        Args:
            user_id: 用户ID
            points_before: 扣除前的积分数量
            reason: 退还原因
        """
        if not self.points_service:
            return
        
        try:
            supabase = supabase_service.get_client()
            supabase.from_("user_profiles").update({
                "points": points_before
            }).eq("user_id", user_id).execute()
            
            logger.info(f"用户 {user_id} 积分全额退还成功: {reason} (出错不收保底费用)")
        except Exception as e:
            logger.error(f"积分退还失败: {e}")
    
    async def adjust_final_points(self, user_id: str, pre_deducted_points: int, actual_points: int) -> bool:
        """
        调整最终积分消费（处理预扣与实际消费的差额）
        
        Args:
            user_id: 用户ID
            pre_deducted_points: 预扣积分数量
            actual_points: 实际消耗积分数量
            
        Returns:
            是否调整成功
        """
        if not self.points_service:
            return True
        
        # 计算差额
        points_diff = actual_points - pre_deducted_points
        
        if points_diff == 0:
            logger.info(f"用户 {user_id} 预扣积分与实际消费一致，无需调整")
            return True
        
        try:
            # 获取当前积分
            balance = await self.points_service.get_user_balance(user_id)
            if not balance:
                logger.error(f"用户 {user_id} 积分余额获取失败")
                return False
            
            current_points = balance.total_points
            
            if points_diff > 0:
                # 实际消费更多，需要额外扣费
                if current_points < points_diff:
                    logger.warning(f"用户 {user_id} 积分不足以支付额外费用: 当前{current_points}, 需要{points_diff}")
                    # 可以选择将用户积分扣为0，或者记录欠费
                    new_points = 0
                else:
                    new_points = current_points - points_diff
                
                logger.info(f"用户 {user_id} 需额外扣费 {points_diff} 积分: {current_points} -> {new_points}")
            else:
                # 实际消费更少，退还差额
                refund_amount = abs(points_diff)
                new_points = current_points + refund_amount
                logger.info(f"用户 {user_id} 退还 {refund_amount} 积分: {current_points} -> {new_points}")
            
            # 更新积分
            supabase = supabase_service.get_client()
            try:
                # 优先使用RPC函数
                rpc_result = supabase.rpc('update_user_points_bypass_rls', {
                    'p_user_id': user_id,
                    'p_new_points': new_points
                }).execute()
                
                if rpc_result.data:
                    logger.info(f"用户 {user_id} 积分调整成功")
                    return True
                else:
                    raise Exception("RPC更新积分失败")
                    
            except Exception as rpc_error:
                logger.warning(f"RPC方法更新积分失败: {rpc_error}，尝试直接更新")
                
                update_result = supabase.from_("user_profiles").update({
                    "points": new_points
                }).eq("user_id", user_id).execute()
                
                if update_result.data:
                    logger.info(f"用户 {user_id} 积分直接更新调整成功")
                    return True
                else:
                    logger.error(f"用户 {user_id} 积分调整失败")
                    return False
                    
        except Exception as e:
            logger.error(f"积分调整异常: {e}")
            return False
    
    async def upload_file(
        self, 
        user_id: str, 
        file_content: bytes, 
        filename: str, 
        content_type: str
    ) -> str:
        """
        上传文件到Dify
        
        Args:
            user_id: 用户ID
            file_content: 文件内容
            filename: 文件名
            content_type: 文件类型
            
        Returns:
            Dify文件ID
        """
        upload_url = f"{self.api_url}/files/upload"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        # 确定文件类型
        def get_file_type(filename: str, content_type: str) -> str:
            if not filename:
                return "TXT"
                
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            # 图片类型
            if ext in ['jpg', 'jpeg']:
                return "JPG"
            elif ext in ['png']:
                return "PNG"
            elif ext in ['gif']:
                return "GIF"
            elif ext in ['webp']:
                return "WEBP"
            elif ext in ['svg']:
                return "SVG"
            # 音频类型
            elif ext in ['mp3']:
                return "MP3"
            elif ext in ['wav']:
                return "WAV"
            elif ext in ['m4a']:
                return "M4A"
            # 文档类型
            elif ext in ['pdf']:
                return "PDF"
            elif ext in ['txt', 'md']:
                return "TXT"
            elif ext in ['docx']:
                return "DOCX"
            elif ext in ['xlsx']:
                return "XLSX"
            else:
                # 根据content_type判断
                if content_type.startswith('image/'):
                    return "JPG"
                elif content_type.startswith('audio/'):
                    return "MP3"
                elif content_type == 'application/pdf':
                    return "PDF"
                else:
                    return "TXT"
        
        file_type = get_file_type(filename, content_type)
        
        files = {
            'file': (filename, file_content, content_type)
        }
        data = {
            "user": user_id,
            "type": file_type
        }
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(upload_url, headers=headers, data=data, files=files)
            
            if response.status_code == 201:
                response_data = response.json()
                file_id = response_data.get("id")
                logger.info(f"文件上传成功: {filename} -> {file_id}")
                return file_id
            else:
                logger.error(f"文件上传失败: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"文件上传失败: {response.text}"
                )
                
        except httpx.RequestError as e:
            logger.error(f"文件上传请求错误: {e}")
            raise HTTPException(status_code=502, detail=f"文件上传请求错误: {str(e)}")
    
    async def chat_stream(
        self,
        user_id: str,
        query: str,
        model: str,
        conversation_id: Optional[str] = None,
        files: Optional[List[Dict[str, Any]]] = None,
        skip_points_deduction: bool = False
    ) -> AsyncIterator[str]:
        """
        与通用助手进行流式聊天
        
        Args:
            user_id: 用户ID
            query: 用户查询
            model: 选择的模型
            conversation_id: 会话ID
            files: 文件列表
            
        Yields:
            流式响应数据
        """
        # 验证模型权限
        await self.validate_model_access(user_id, model)
        
        # 根据参数决定是否预扣积分
        points_deducted = False
        points_before = 0
        if not skip_points_deduction:
            points_deducted, points_before, _ = await self.deduct_points_for_model(user_id, model)
        
        # 如果提供了conversation_id，获取对应的dify_conversation_id
        dify_conversation_id = None
        if conversation_id:
            from app.services.dify_conversation_service import DifyConversationService
            conversation_service = DifyConversationService()
            conversation = await conversation_service.get_conversation(user_id, conversation_id, access_token=None)
            if conversation and conversation.dify_conversation_id:
                dify_conversation_id = conversation.dify_conversation_id
        
        # 准备请求数据
        payload = {
            "inputs": {"model": model},
            "query": query,
            "response_mode": "streaming",
            "user": user_id,
        }
        
        # 只有当存在Dify会话ID时才添加到请求中
        if dify_conversation_id:
            payload["conversation_id"] = dify_conversation_id
        
        if files:
            payload["files"] = files
            
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.info(f"发起通用助手请求: 模型={model}, 用户={user_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_url}/chat-messages",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"通用助手API错误: {response.status_code} - {error_text}")
                        
                        if points_deducted:
                            await self.refund_points(user_id, points_before, "API调用失败")
                        
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"通用助手API调用失败: {error_text.decode()}"
                        )
                    
                    # 简化逻辑：只提取并转发来自Dify的JSON数据流
                    async for chunk in response.aiter_lines():
                        if chunk.strip().startswith("data:"):
                            data_str = chunk.strip()[6:]
                            if data_str and data_str != '[DONE]':
                                yield data_str
                                
        except httpx.TimeoutException:
            if points_deducted:
                await self.refund_points(user_id, points_before, "请求超时")
            raise HTTPException(status_code=504, detail="通用助手API请求超时")
        except httpx.RequestError as e:
            if points_deducted:
                await self.refund_points(user_id, points_before, f"请求错误: {str(e)}")
            raise HTTPException(status_code=502, detail=f"通用助手API请求错误: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            if points_deducted:
                await self.refund_points(user_id, points_before, f"未知错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"通用助手服务错误: {str(e)}")
    
    async def update_dify_conversation_id(self, conversation_id: str, dify_conversation_id: str):
        """在后台更新数据库中的 Dify conversation ID"""
        try:
            from app.services.dify_conversation_service import DifyConversationService
            conversation_service = DifyConversationService()
            await conversation_service.update_conversation_dify_id(
                conversation_id, dify_conversation_id
            )
            logger.info(f"后台更新会话Dify ID成功: {conversation_id} -> {dify_conversation_id}")
        except Exception as e:
            logger.warning(f"后台更新会话Dify ID失败: {e}")

    async def get_available_models(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户可用的模型列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            可用模型列表
        """
        try:
            # 获取用户等级
            user_service = UserService()
            profile = await user_service.get_user_profile(user_id)
            user_tier = profile.get("tier", "free") if profile else "free"
            
            tier_hierarchy = {"free": 0, "plus": 1, "pro": 2, "max": 3}
            user_level = tier_hierarchy.get(user_tier, 0)
            
            available_models = []
            for model_id, model_config in self.supported_models.items():
                if not model_config.is_active:
                    continue
                
                required_level = tier_hierarchy.get(model_config.required_tier, 0)
                
                model_info = {
                    "id": model_config.id,
                    "name": model_config.name,
                    "description": model_config.description,
                    "capabilities": model_config.capabilities,
                    "supported_file_types": model_config.supported_file_types,
                    "max_tokens": model_config.max_tokens,
                    "required_tier": model_config.required_tier,
                    "input_token_cost": model_config.input_token_cost,
                    "output_token_cost": model_config.output_token_cost,
                    "base_cost": model_config.base_cost,
                    "available": user_level >= required_level
                }
                
                available_models.append(model_info)
            
            return available_models
            
        except Exception as e:
            logger.error(f"获取可用模型列表失败: {e}")
            raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}") 