"""
增强的AI服务模块
集成统一配置、积分系统和用户权限控制
"""

import logging
import uuid
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
import structlog
import asyncio
import json

from ..core.config import settings
from ..core.ai_models_config import (
    ai_models_config, 
    UserTier, 
    ModelConfig, 
    ModelCapability,
    get_user_tier_from_subscription
)
from ..services.points_service import points_service
from ..schemas.points import ServiceType, ConsumePointsRequest

logger = structlog.get_logger()


class EnhancedAIService:
    """增强的AI服务类，支持统一配置和积分管理"""
    
    def __init__(self):
        self._clients_cache: Dict[str, Any] = {}
        self._init_clients()
    
    def _init_clients(self):
        """初始化AI客户端"""
        try:
            # 为每个活跃的模型创建客户端
            for model_id, model_config in ai_models_config.models.items():
                if not model_config.is_active:
                    continue
                    
                self._create_client_for_model(model_config)
                
            logger.info("AI clients initialized", total_models=len(self._clients_cache))
            
        except Exception as e:
            logger.error(f"Failed to initialize AI clients: {e}")
    
    def _create_client_for_model(self, model_config: ModelConfig):
        """为特定模型创建客户端"""
        try:
            if model_config.provider.value == "gemini" and settings.google_api_key:
                client = ChatGoogleGenerativeAI(
                    model=model_config.aimodel_key,
                    google_api_key=settings.google_api_key,
                    temperature=settings.temperature,
                    max_tokens=model_config.max_tokens,
                    timeout=settings.ai_request_timeout
                )
                self._clients_cache[model_config.id] = client
                
            elif model_config.provider.value == "openrouter" and settings.openrouter_api_key:
                client = ChatOpenAI(
                    model=model_config.aimodel_key,
                    openai_api_key=settings.openrouter_api_key,
                    openai_api_base=settings.openrouter_base_url,
                    temperature=settings.temperature,
                    max_tokens=model_config.max_tokens,
                    timeout=settings.ai_request_timeout
                )
                self._clients_cache[model_config.id] = client
                
            elif model_config.provider.value == "qwen_translation" and settings.dashscope_api_key:
                client = ChatOpenAI(
                    model=model_config.aimodel_key,
                    openai_api_key=settings.dashscope_api_key,
                    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    temperature=0.1,  # 翻译使用较低的temperature
                    max_tokens=model_config.max_tokens,
                    timeout=settings.ai_request_timeout
                )
                self._clients_cache[model_config.id] = client
                
        except Exception as e:
            logger.error(f"Failed to create client for model {model_config.id}: {e}")
    
    def _get_client(self, model_id: str):
        """获取指定模型的客户端"""
        return self._clients_cache.get(model_id)
    
    async def get_available_models(
        self, 
        user_subscription: str = "free",
        capability: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取用户可用的模型列表
        
        Args:
            user_subscription: 用户订阅级别
            capability: 所需能力（可选）
            
        Returns:
            可用模型列表
        """
        user_tier = get_user_tier_from_subscription(user_subscription)
        capability_enum = ModelCapability(capability) if capability else None
        
        available_models = ai_models_config.get_available_models(user_tier, capability_enum)
        
        result = []
        for model in available_models:
            # 检查客户端是否可用
            client_available = model.id in self._clients_cache
            
            model_info = {
                "id": model.id,
                "name": model.name,
                "provider": model.provider.value,
                "description": model.description,
                "capabilities": [cap.value for cap in model.capabilities],
                "max_tokens": model.max_tokens,
                "supports_vision": model.supports_vision,
                "supports_function_calling": model.supports_function_calling,
                "billing_type": model.billing_type.value,
                "points_cost": {
                    "base_points": model.base_points,
                    "per_1k_tokens": model.points_per_1k_tokens,
                    "per_request": model.points_per_request,
                    "per_100_chars": model.points_per_100_chars
                },
                "use_cases": model.use_cases,
                "limitations": model.limitations,
                "is_beta": model.is_beta,
                "rate_limit_per_minute": model.rate_limit_per_minute,
                "available": client_available
            }
            result.append(model_info)
        
        return result
    
    async def get_all_active_models(
        self, 
        capability: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取所有活跃的模型列表（不进行权限过滤）
        
        Args:
            capability: 所需能力（可选）
            
        Returns:
            所有活跃模型列表，包含权限信息
        """
        capability_enum = ModelCapability(capability) if capability else None
        
        all_models = ai_models_config.get_all_active_models(capability_enum)
        
        result = []
        for model in all_models:
            # 检查客户端是否可用
            client_available = model.id in self._clients_cache
            
            model_info = {
                "id": model.id,
                "name": model.name,
                "provider": model.provider.value,
                "description": model.description,
                "capabilities": [cap.value for cap in model.capabilities],
                "max_tokens": model.max_tokens,
                "supports_vision": model.supports_vision,
                "supports_function_calling": model.supports_function_calling,
                "required_tier": model.required_tier.value,  # 添加所需会员等级信息
                "billing_type": model.billing_type.value,
                "points_per_1k_tokens": model.points_per_1k_tokens,  # 简化积分信息
                "points_cost": {
                    "base_points": model.base_points,
                    "per_1k_tokens": model.points_per_1k_tokens,
                    "per_request": model.points_per_request,
                    "per_100_chars": model.points_per_100_chars
                },
                "use_cases": model.use_cases,
                "limitations": model.limitations,
                "is_beta": model.is_beta,
                "rate_limit_per_minute": model.rate_limit_per_minute,
                "available": client_available
            }
            result.append(model_info)
        
        return result
    
    async def chat_completion_with_points(
        self,
        user_id: str,
        user_subscription: str,
        model_id: str,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        auto_charge: bool = True
    ) -> Dict[str, Any]:
        """
        执行聊天完成（集成积分扣费）
        
        Args:
            user_id: 用户ID
            user_subscription: 用户订阅级别
            model_id: 模型ID
            message: 用户消息
            system_prompt: 系统提示词
            conversation_history: 对话历史
            auto_charge: 是否自动扣费
            
        Returns:
            包含AI响应和积分信息的字典
        """
        try:
            # 1. 验证用户权限
            user_tier = get_user_tier_from_subscription(user_subscription)
            if not ai_models_config.can_user_access_model(user_tier, model_id):
                return {
                    "success": False,
                    "error": "model_access_denied",
                    "message": f"用户级别 {user_subscription} 无权访问模型 {model_id}"
                }
            
            # 2. 获取模型配置和客户端
            model_config = ai_models_config.get_model(model_id)
            if not model_config:
                return {
                    "success": False,
                    "error": "model_not_found",
                    "message": f"模型 {model_id} 不存在"
                }
            
            client = self._get_client(model_id)
            if not client:
                return {
                    "success": False,
                    "error": "client_unavailable",
                    "message": f"模型 {model_id} 的客户端不可用"
                }
            
            # 3. 估算token使用量并检查积分
            estimated_tokens = len(message) // 4  # 粗略估算
            if system_prompt:
                estimated_tokens += len(system_prompt) // 4
            if conversation_history:
                for msg in conversation_history:
                    estimated_tokens += len(msg.get("content", "")) // 4
            
            points_needed = ai_models_config.calculate_points_cost(
                model_id, estimated_tokens
            )
            
            # 4. 积分预检查（如果需要扣费）
            logger.info(f"积分检查开始 - 用户: {user_id}, 预估消耗: {points_needed}, 自动扣费: {auto_charge}")
            
            if auto_charge and points_needed > 0:
                # 直接获取用户余额进行简单检查
                balance = await points_service.get_user_balance(user_id)
                logger.info(f"获取到的用户余额: {balance.total_points if balance else 'None'}")
                
                if not balance:
                    logger.error(f"无法获取用户 {user_id} 的积分余额")
                    return {
                        "success": False,
                        "error": "balance_check_failed",
                        "message": "无法获取用户积分余额"
                    }
                
                current_points = balance.total_points
                logger.info(f"积分比较 - 当前积分: {current_points}, 需要积分: {points_needed}")
                
                if current_points < points_needed:
                    logger.warning(f"积分不足 - 用户: {user_id}, 当前: {current_points}, 需要: {points_needed}")
                    return {
                        "success": False,
                        "error": "insufficient_points",
                        "message": "积分不足",
                        "current_points": current_points,
                        "required_points": points_needed,
                        "shortfall": points_needed - current_points
                    }
            
            logger.info(f"积分检查通过 - 用户: {user_id}")
            
            
            # 5. 执行AI调用
            messages = []
            
            # 添加系统消息
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加对话历史
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            # 添加当前用户消息
            messages.append(HumanMessage(content=message))
            
            # 调用AI
            response = await client.ainvoke(messages)
            
            # 6. 计算实际token使用量
            actual_tokens = getattr(response, 'usage_metadata', {}).get('total_tokens', estimated_tokens)
            actual_points_cost = ai_models_config.calculate_points_cost(
                model_id, actual_tokens
            )
            
            # 7. 扣费（如果启用自动扣费且有积分消耗）
            points_transaction = None
            if auto_charge and actual_points_cost > 0:
                # 简化的积分扣费：直接更新用户积分
                try:
                    # 获取当前积分
                    balance = await points_service.get_user_balance(user_id)
                    if balance and balance.total_points >= actual_points_cost:
                        # 直接扣除积分
                        new_balance = balance.total_points - actual_points_cost
                        
                        # 生成交易ID
                        transaction_id = str(uuid.uuid4())
                        request_id = f"ai_chat_{user_id}_{int(datetime.now().timestamp())}"
                        
                        # 1. 更新 user_profiles 表中的积分
                        update_response = points_service.supabase.table("user_profiles").update({
                            "points": new_balance,
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).execute()
                        
                        if update_response.data:
                            # 2. 插入交易记录到 user_point_transactions 表
                            transaction_data = {
                                "id": transaction_id,
                                "user_id": user_id,
                                "transaction_type": "consume",
                                "points_change": -actual_points_cost,  # 消费为负数
                                "points_before": balance.total_points,
                                "points_after": new_balance,
                                "service_type": "ai_chat",
                                "aimodel_name": model_id,
                                "tokens_used": actual_tokens,
                                "status": "completed",
                                "description": f"AI聊天 - {model_config.name}",
                                "request_id": request_id,
                                "service_details": {
                                    "model_config": {
                                        "id": model_id,
                                        "name": model_config.name,
                                        "provider": model_config.provider.value
                                    },
                                    "usage": {
                                        "total_tokens": actual_tokens,
                                        "points_cost": actual_points_cost
                                    }
                                },
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                            
                            transaction_insert_response = points_service.supabase.table("user_point_transactions").insert(transaction_data).execute()
                            
                            if transaction_insert_response.data:
                                points_transaction = {
                                    "transaction_id": transaction_id,
                                    "points_consumed": actual_points_cost,
                                    "points_before": balance.total_points,
                                    "points_after": new_balance
                                }
                                
                                logger.info(
                                    f"Points consumed and recorded successfully: {actual_points_cost} points",
                                    user_id=user_id,
                                    model_id=model_id,
                                    transaction_id=transaction_id,
                                    points_before=balance.total_points,
                                    points_after=new_balance
                                )
                            else:
                                logger.warning(
                                    "Failed to insert transaction record",
                                    user_id=user_id,
                                    model_id=model_id,
                                    transaction_id=transaction_id
                                )
                                # 即使交易记录失败，积分已经扣除了，返回成功
                                points_transaction = {
                                    "transaction_id": transaction_id,
                                    "points_consumed": actual_points_cost,
                                    "points_before": balance.total_points,
                                    "points_after": new_balance
                                }
                        else:
                            logger.warning(
                                "Failed to update points balance",
                                user_id=user_id,
                                model_id=model_id
                            )
                    else:
                        logger.warning(
                            "Insufficient points for consumption",
                            user_id=user_id,
                            model_id=model_id,
                            current_points=balance.total_points if balance else 0,
                            required_points=actual_points_cost
                        )
                        
                except Exception as e:
                    logger.warning(
                        "Points consumption failed due to exception",
                        user_id=user_id,
                        model_id=model_id,
                        error=str(e)
                    )
            
            return {
                "success": True,
                "content": response.content,
                "model": {
                    "id": model_id,
                    "name": model_config.name,
                    "provider": model_config.provider.value
                },
                "usage": {
                    "total_tokens": actual_tokens,
                    "estimated_tokens": estimated_tokens,
                    "points_cost": actual_points_cost
                },
                "points_transaction": points_transaction
            }
            
        except Exception as e:
            logger.error(
                f"Chat completion failed: {e}", 
                user_id=user_id, 
                model_id=model_id,
                user_subscription=user_subscription,
                error_type=type(e).__name__,
                error_details=str(e)
            )
            return {
                "success": False,
                "error": "ai_call_failed",
                "message": str(e)
            }
    
    async def chat_completion_with_points_stream(
        self,
        user_id: str,
        user_subscription: str,
        model_id: str,
        message: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        auto_charge: bool = True
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行流式聊天完成（集成积分扣费）
        
        Args:
            user_id: 用户ID
            user_subscription: 用户订阅级别
            model_id: 模型ID
            message: 用户消息
            system_prompt: 系统提示词
            conversation_history: 对话历史
            auto_charge: 是否自动扣费
            
        Yields:
            包含流式响应的字典
        """
        try:
            # 1. 验证用户权限
            user_tier = get_user_tier_from_subscription(user_subscription)
            if not ai_models_config.can_user_access_model(user_tier, model_id):
                yield {
                    "success": False,
                    "error": "model_access_denied",
                    "message": f"用户级别 {user_subscription} 无权访问模型 {model_id}"
                }
                return
            
            # 2. 获取模型配置和客户端
            model_config = ai_models_config.get_model(model_id)
            if not model_config:
                yield {
                    "success": False,
                    "error": "model_not_found",
                    "message": f"模型 {model_id} 不存在"
                }
                return
            
            client = self._get_client(model_id)
            if not client:
                yield {
                    "success": False,
                    "error": "client_unavailable",
                    "message": f"模型 {model_id} 的客户端不可用"
                }
                return
            
            # 3. 估算token使用量并检查积分
            estimated_tokens = len(message) // 4  # 粗略估算
            if system_prompt:
                estimated_tokens += len(system_prompt) // 4
            if conversation_history:
                for msg in conversation_history:
                    estimated_tokens += len(msg.get("content", "")) // 4
            
            points_needed = ai_models_config.calculate_points_cost(
                model_id, estimated_tokens
            )
            
            # 4. 积分预检查（如果需要扣费）
            if auto_charge and points_needed > 0:
                balance = await points_service.get_user_balance(user_id)
                
                if not balance:
                    yield {
                        "success": False,
                        "error": "balance_check_failed",
                        "message": "无法获取用户积分余额"
                    }
                    return
                
                current_points = balance.total_points
                
                if current_points < points_needed:
                    yield {
                        "success": False,
                        "error": "insufficient_points",
                        "message": "积分不足",
                        "current_points": current_points,
                        "required_points": points_needed,
                        "shortfall": points_needed - current_points
                    }
                    return
            
            # 5. 准备消息
            messages = []
            
            # 添加系统消息
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加对话历史
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            # 添加当前用户消息
            messages.append(HumanMessage(content=message))
            
            # 6. 发送开始事件
            yield {
                "event": "start",
                "model": {
                    "id": model_id,
                    "name": model_config.name,
                    "provider": model_config.provider.value
                },
                "estimated_points": points_needed
            }
            
            # 7. 执行流式AI调用
            full_response = ""
            actual_tokens = estimated_tokens  # 默认值
            
            try:
                # 使用流式调用
                async for chunk in client.astream(messages):
                    if hasattr(chunk, 'content') and chunk.content:
                        full_response += chunk.content
                        yield {
                            "event": "chunk",
                            "content": chunk.content
                        }
                        
                        # 添加小延迟以创建打字机效果
                        await asyncio.sleep(0.01)
                
                # 尝试获取实际token使用量
                # 注意：不同的provider可能有不同的token计算方式
                actual_tokens = len(full_response) // 4 + estimated_tokens
                
            except Exception as e:
                logger.error(f"Streaming AI call failed: {e}", user_id=user_id, model_id=model_id)
                yield {
                    "event": "error",
                    "message": f"AI调用失败: {str(e)}"
                }
                return
            
            # 8. 计算实际积分消耗
            actual_points_cost = ai_models_config.calculate_points_cost(
                model_id, actual_tokens
            )
            
            # 9. 扣费（如果启用自动扣费且有积分消耗）
            points_transaction = None
            if auto_charge and actual_points_cost > 0:
                try:
                    balance = await points_service.get_user_balance(user_id)
                    if balance and balance.total_points >= actual_points_cost:
                        # 直接扣除积分
                        new_balance = balance.total_points - actual_points_cost
                        
                        # 生成交易ID
                        transaction_id = str(uuid.uuid4())
                        request_id = f"ai_stream_chat_{user_id}_{int(datetime.now().timestamp())}"
                        
                        # 更新积分
                        update_response = points_service.supabase.table("user_profiles").update({
                            "points": new_balance,
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).execute()
                        
                        if update_response.data:
                            # 插入交易记录
                            transaction_data = {
                                "id": transaction_id,
                                "user_id": user_id,
                                "transaction_type": "consume",
                                "points_change": -actual_points_cost,
                                "points_before": balance.total_points,
                                "points_after": new_balance,
                                "service_type": "ai_stream_chat",
                                "aimodel_name": model_id,
                                "tokens_used": actual_tokens,
                                "status": "completed",
                                "description": f"AI流式聊天 - {model_config.name}",
                                "request_id": request_id,
                                "service_details": {
                                    "model_config": {
                                        "id": model_id,
                                        "name": model_config.name,
                                        "provider": model_config.provider.value
                                    },
                                    "usage": {
                                        "total_tokens": actual_tokens,
                                        "points_cost": actual_points_cost
                                    }
                                },
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                            
                            points_service.supabase.table("user_point_transactions").insert(transaction_data).execute()
                            
                            points_transaction = {
                                "transaction_id": transaction_id,
                                "points_consumed": actual_points_cost,
                                "points_before": balance.total_points,
                                "points_after": new_balance
                            }
                            
                except Exception as e:
                    logger.warning(f"Points consumption failed: {e}", user_id=user_id, model_id=model_id)
            
            # 10. 发送完成事件
            yield {
                "event": "complete",
                "full_response": full_response,
                "usage": {
                    "total_tokens": actual_tokens,
                    "estimated_tokens": estimated_tokens,
                    "points_cost": actual_points_cost
                },
                "points_transaction": points_transaction
            }
            
        except Exception as e:
            logger.error(f"Stream chat completion failed: {e}", user_id=user_id, model_id=model_id)
            yield {
                "event": "error",
                "message": f"流式聊天失败: {str(e)}"
            }
    
    async def text_analysis_with_points(
        self,
        user_id: str,
        user_subscription: str,
        model_id: str,
        text: str,
        analysis_type: str = "explain",
        target_language: str = "zh",
        user_native_language: str = "zh",
        user_language_level: str = "beginner",
        auto_charge: bool = True
    ) -> Dict[str, Any]:
        """
        文本分析功能（集成积分扣费）
        """
        # 语言映射字典
        language_names = {
            "zh": "中文",
            "en": "英文", 
            "ja": "日语",
            "ko": "韩语",
            "es": "西班牙语",
            "fr": "法语"
        }
        
        native_lang_name = language_names.get(user_native_language, "中文")
        target_lang_name = language_names.get(target_language, "中文")
        
        # 构建系统提示词（根据用户语言设置动态调整）
        system_prompts = {
            "explain": f"你是一个专业的语言学习助手。用户的母语是{native_lang_name}，语言水平是{user_language_level}。请用{target_lang_name}详细解释用户提供的文本内容，包括词汇、语法、文化背景等。请根据用户的{user_language_level}水平调整解释的深度和复杂度，使用适合该水平学习者的表达方式。",
            "translate": f"你是一个专业的翻译助手。用户的母语是{native_lang_name}。请将用户提供的文本准确翻译成{target_lang_name}，并用{native_lang_name}简要说明翻译要点，帮助理解原文的含义和表达方式。",
            "summarize": f"你是一个专业的文本总结助手。用户的母语是{native_lang_name}，语言水平是{user_language_level}。请用{target_lang_name}对用户提供的文本进行简洁而全面的总结，并确保内容适合{user_language_level}水平的学习者理解。"
        }
        
        system_prompt = system_prompts.get(analysis_type, system_prompts["explain"])
        
        return await self.chat_completion_with_points(
            user_id=user_id,
            user_subscription=user_subscription,
            model_id=model_id,
            message=f"请分析以下文本：\n\n{text}",
            system_prompt=system_prompt,
            auto_charge=auto_charge
        )
    
    async def calculate_cost_preview(
        self,
        model_id: str,
        text_length: int
    ) -> Dict[str, Any]:
        """
        计算操作成本预览
        
        Args:
            model_id: 模型ID
            text_length: 文本长度
            
        Returns:
            成本预览信息
        """
        model_config = ai_models_config.get_model(model_id)
        if not model_config:
            return {"error": "模型不存在"}
        
        estimated_tokens = text_length // 4
        estimated_cost = ai_models_config.calculate_points_cost(model_id, estimated_tokens)
        
        return {
            "model": {
                "id": model_id,
                "name": model_config.name,
                "billing_type": model_config.billing_type.value
            },
            "estimated_tokens": estimated_tokens,
            "estimated_points": estimated_cost,
            "pricing_info": {
                "base_points": model_config.base_points,
                "per_1k_tokens": model_config.points_per_1k_tokens,
                "per_request": model_config.points_per_request
            }
        }

    async def translation_with_points(
        self,
        user_id: str,
        user_subscription: str,
        content: str,
        source_lang: str,
        target_lang: str,
        auto_charge: bool = True,
        model_id: str = "qwen-mt-turbo"
    ) -> Dict[str, Any]:
        """
        执行翻译并扣费
        
        Args:
            user_id: 用户ID
            user_subscription: 用户订阅级别
            content: 要翻译的内容
            source_lang: 源语言
            target_lang: 目标语言
            auto_charge: 是否自动扣费
            model_id: 翻译模型ID
            
        Returns:
            包含翻译结果和积分信息的字典
        """
        try:
            # 1. 验证用户权限
            user_tier = get_user_tier_from_subscription(user_subscription)
            if not ai_models_config.can_user_access_model(user_tier, model_id):
                return {
                    "success": False,
                    "error": "model_access_denied",
                    "message": f"用户级别 {user_subscription} 无权访问模型 {model_id}"
                }
            
            # 2. 获取模型配置和客户端
            model_config = ai_models_config.get_model(model_id)
            if not model_config:
                return {
                    "success": False,
                    "error": "model_not_found",
                    "message": f"模型 {model_id} 不存在"
                }
            
            client = self._get_client(model_id)
            if not client:
                return {
                    "success": False,
                    "error": "client_unavailable",
                    "message": f"模型 {model_id} 的客户端不可用"
                }
            
            # 3. 估算token使用量并检查积分
            estimated_tokens = len(content) // 4  # 粗略估算
            points_needed = ai_models_config.calculate_points_cost(
                model_id, estimated_tokens
            )
            
            # 4. 积分预检查（如果需要扣费）
            logger.info(f"翻译积分检查开始 - 用户: {user_id}, 预估消耗: {points_needed}, 自动扣费: {auto_charge}")
            
            if auto_charge and points_needed > 0:
                balance = await points_service.get_user_balance(user_id)
                logger.info(f"获取到的用户余额: {balance.total_points if balance else 'None'}")
                
                if not balance:
                    logger.error(f"无法获取用户 {user_id} 的积分余额")
                    return {
                        "success": False,
                        "error": "balance_check_failed",
                        "message": "无法获取用户积分余额"
                    }
                
                current_points = balance.total_points
                logger.info(f"积分比较 - 当前积分: {current_points}, 需要积分: {points_needed}")
                
                if current_points < points_needed:
                    logger.warning(f"积分不足 - 用户: {user_id}, 当前: {current_points}, 需要: {points_needed}")
                    return {
                        "success": False,
                        "error": "insufficient_points",
                        "message": "积分不足",
                        "current_points": current_points,
                        "required_points": points_needed,
                        "shortfall": points_needed - current_points
                    }
            
            logger.info(f"翻译积分检查通过 - 用户: {user_id}")
            
            # 5. 构建翻译请求
            # 根据demo代码使用extra_body
            translation_options = {
                "source_lang": source_lang,
                "target_lang": target_lang
            }
            
            messages = [HumanMessage(content=content)]
            
            # 调用翻译API
            response = await client.ainvoke(
                messages,
                extra_body={"translation_options": translation_options}
            )
            
            # 6. 计算实际token使用量
            actual_tokens = getattr(response, 'usage_metadata', {}).get('total_tokens', estimated_tokens)
            actual_points_cost = ai_models_config.calculate_points_cost(
                model_id, actual_tokens
            )
            
            # 7. 扣费（如果启用自动扣费且有积分消耗）
            current_balance = None
            if auto_charge and actual_points_cost > 0:
                try:
                    # 获取当前积分
                    balance = await points_service.get_user_balance(user_id)
                    if balance and balance.total_points >= actual_points_cost:
                        # 直接扣除积分
                        new_balance = balance.total_points - actual_points_cost
                        current_balance = new_balance
                        
                        # 生成交易ID
                        transaction_id = str(uuid.uuid4())
                        request_id = f"translation_{user_id}_{int(datetime.now().timestamp())}"
                        
                        # 更新用户积分
                        update_response = points_service.supabase.table("user_profiles").update({
                            "points": new_balance,
                            "updated_at": datetime.now().isoformat()
                        }).eq("user_id", user_id).execute()
                        
                        if update_response.data:
                            # 插入交易记录
                            transaction_data = {
                                "id": transaction_id,
                                "user_id": user_id,
                                "transaction_type": "consume",
                                "points_change": -actual_points_cost,
                                "points_before": balance.total_points,
                                "points_after": new_balance,
                                "service_type": "translation",
                                "aimodel_name": model_id,
                                "tokens_used": actual_tokens,
                                "status": "completed",
                                "description": f"文本翻译 - {model_config.name}",
                                "request_id": request_id,
                                "service_details": {
                                    "model_config": {
                                        "id": model_id,
                                        "name": model_config.name,
                                        "provider": model_config.provider.value
                                    },
                                    "translation_info": {
                                        "source_lang": source_lang,
                                        "target_lang": target_lang,
                                        "content_length": len(content)
                                    },
                                    "tokens_used": actual_tokens,
                                    "points_cost": actual_points_cost
                                }
                            }
                            
                            points_service.supabase.table("user_point_transactions").insert(transaction_data).execute()
                            logger.info(f"翻译积分扣费成功 - 用户: {user_id}, 消耗: {actual_points_cost}, 余额: {new_balance}")
                    else:
                        logger.error(f"翻译扣费失败 - 积分不足或获取失败")
                        return {
                            "success": False,
                            "error": "insufficient_points_final",
                            "message": "扣费时发现积分不足"
                        }
                except Exception as e:
                    logger.error(f"翻译扣费过程中出错: {e}")
                    return {
                        "success": False,
                        "error": "billing_error",
                        "message": "扣费过程中出现错误"
                    }
            
            # 8. 返回成功结果
            return {
                "success": True,
                "translated_text": response.content,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "tokens_used": actual_tokens,
                "points_consumed": actual_points_cost if auto_charge else 0,
                "current_points": current_balance,
                "model": {
                    "id": model_id,
                    "name": model_config.name,
                    "provider": model_config.provider.value
                }
            }
            
        except Exception as e:
            logger.error(f"翻译服务错误: {e}")
            return {
                "success": False,
                "error": "translation_error",
                "message": f"翻译过程中出现错误: {str(e)}"
            }
    
    def reload_models_config(self):
        """重新加载模型配置"""
        ai_models_config.reload_config()
        self._clients_cache.clear()
        self._init_clients()
        logger.info("AI models configuration reloaded")


# 创建全局增强AI服务实例
enhanced_ai_service = EnhancedAIService()