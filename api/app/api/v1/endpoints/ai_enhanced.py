"""
增强的AI API端点
集成统一配置、积分系统和用户权限控制
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import structlog
import json

from ....services.enhanced_ai_service import enhanced_ai_service
from ....services.material_service import material_service
from ....services.user_service import user_service
from ....core.dependencies import get_current_user, get_current_user_with_token
from ....schemas.auth import UserResponse
from ....schemas.user import UserCompleteProfile

logger = structlog.get_logger()

router = APIRouter()


# 请求模型
class EnhancedChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    aimodel_id: str = Field(..., description="模型ID")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="对话历史")
    auto_charge: bool = Field(True, description="是否自动扣费")


class EnhancedAnalysisRequest(BaseModel):
    text: str = Field(..., description="要分析的文本")
    aimodel_id: str = Field(..., description="模型ID")
    analysis_type: str = Field("explain", description="分析类型: explain, translate, summarize")
    target_language: str = Field("zh", description="目标语言")
    auto_charge: bool = Field(True, description="是否自动扣费")


class CostPreviewRequest(BaseModel):
    aimodel_id: str = Field(..., description="模型ID")
    text_length: int = Field(..., description="预估文本长度")


class ArticleChatRequest(BaseModel):
    article_id: str = Field(..., description="文章ID")
    message: str = Field(..., description="用户消息")
    aimodel_id: str = Field(..., description="模型ID")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="对话历史")
    auto_charge: bool = Field(True, description="是否自动扣费")


class SegmentsChatRequest(BaseModel):
    article_id: str = Field(..., description="文章ID")
    segment_ids: List[str] = Field(..., description="段落ID列表")
    message: str = Field(..., description="用户消息")
    aimodel_id: str = Field(..., description="模型ID")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="对话历史")
    auto_charge: bool = Field(True, description="是否自动扣费")


# 响应模型
class EnhancedAIResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None
    model: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    points_transaction: Optional[Dict[str, Any]] = None


class ModelListResponse(BaseModel):
    success: bool
    models: List[Dict[str, Any]]
    user_tier: str
    total_available: int


class CostPreviewResponse(BaseModel):
    success: bool
    model: Optional[Dict[str, Any]] = None
    estimated_tokens: Optional[int] = None
    estimated_points: Optional[int] = None
    pricing_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/models", response_model=ModelListResponse)
async def get_available_models(
    capability: Optional[str] = Query(None, description="筛选特定能力的模型"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取用户可用的AI模型列表
    根据用户订阅级别返回相应的模型
    """
    current_user, access_token = user_info
    try:
        # 获取用户完整信息（包括订阅信息）
        # 这里假设从用户信息中获取订阅级别
        user_subscription = "free"  # 默认免费用户
        
        # TODO: 从用户服务获取实际的订阅信息
        # user_profile = await user_service.get_complete_profile(current_user.id)
        # user_subscription = user_profile.plan_type if user_profile else "free"
        
        models = await enhanced_ai_service.get_available_models(
            user_subscription=user_subscription,
            capability=capability
        )
        
        return ModelListResponse(
            success=True,
            models=models,
            user_tier=user_subscription,
            total_available=len(models)
        )
        
    except Exception as e:
        logger.error(f"Get models error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.get("/models/all", response_model=ModelListResponse)
async def get_all_active_models(
    capability: Optional[str] = Query(None, description="筛选特定能力的模型"),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取所有活跃的AI模型列表（不进行权限过滤）
    用于前端显示所有模型并在客户端控制权限
    """
    current_user, access_token = user_info
    try:
        models = await enhanced_ai_service.get_all_active_models(
            capability=capability
        )
        
        return ModelListResponse(
            success=True,
            models=models,
            user_tier="all",  # 因为这个端点不过滤用户等级，设为all
            total_available=len(models)
        )
        
    except Exception as e:
        logger.error(f"获取所有模型列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取所有模型列表失败: {str(e)}"
        )


@router.post("/chat", response_model=EnhancedAIResponse)
async def enhanced_chat_completion(
    request: EnhancedChatRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    增强的AI聊天接口
    支持用户权限验证、积分扣费等功能
    """
    current_user, access_token = user_info
    try:
        # 获取用户订阅级别
        user_subscription = "free"  # 默认值
        # TODO: 从用户服务获取实际订阅信息
        
        result = await enhanced_ai_service.chat_completion_with_points(
            user_id=current_user.id,
            user_subscription=user_subscription,
            model_id=request.aimodel_id,
            message=request.message,
            system_prompt=request.system_prompt,
            conversation_history=request.conversation_history,
            auto_charge=request.auto_charge
        )
        
        if not result["success"]:
            # 根据错误类型返回不同的HTTP状态码
            error_code = result.get("error", "unknown_error")
            
            if error_code == "model_access_denied":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.get("message", "模型访问被拒绝")
                )
            elif error_code == "insufficient_points":
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "message": result.get("message", "积分不足"),
                        "current_points": result.get("current_points"),
                        "required_points": result.get("required_points"),
                        "shortfall": result.get("shortfall")
                    }
                )
            elif error_code in ["model_not_found", "client_unavailable"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=result.get("message", "模型不可用")
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "AI服务调用失败")
                )
        
        return EnhancedAIResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced chat completion error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"聊天服务异常: {str(e)}"
        )


@router.post("/analyze", response_model=EnhancedAIResponse)
async def enhanced_text_analysis(
    request: EnhancedAnalysisRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    增强的文本分析接口
    """
    current_user, access_token = user_info
    try:
        # 验证分析类型
        valid_types = ["explain", "translate", "summarize"]
        if request.analysis_type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的分析类型。有效选项: {valid_types}"
            )
        
        # 获取用户订阅级别
        user_subscription = "free"
        # TODO: 从用户服务获取实际订阅信息
        
        # 获取用户语言设置
        user_profile = await user_service.get_user_profile(current_user.id)
        user_native_language = "zh"  # 默认中文
        user_language_level = "beginner"  # 默认初学者
        
        if user_profile:
            user_native_language = user_profile.get("native_language", "zh")
            user_language_level = user_profile.get("language_level", "beginner")
        
        result = await enhanced_ai_service.text_analysis_with_points(
            user_id=current_user.id,
            user_subscription=user_subscription,
            model_id=request.aimodel_id,
            text=request.text,
            analysis_type=request.analysis_type,
            target_language=request.target_language,
            user_native_language=user_native_language,
            user_language_level=user_language_level,
            auto_charge=request.auto_charge
        )
        
        if not result["success"]:
            error_code = result.get("error", "unknown_error")
            
            if error_code == "model_access_denied":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=result.get("message", "模型访问被拒绝")
                )
            elif error_code == "insufficient_points":
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "message": result.get("message", "积分不足"),
                        "current_points": result.get("current_points"),
                        "required_points": result.get("required_points"),
                        "shortfall": result.get("shortfall")
                    }
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result.get("message", "分析服务失败")
                )
        
        return EnhancedAIResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enhanced text analysis error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文本分析异常: {str(e)}"
        )


@router.post("/cost-preview", response_model=CostPreviewResponse)
async def get_cost_preview(
    request: CostPreviewRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取操作成本预览
    """
    current_user, access_token = user_info
    try:
        result = await enhanced_ai_service.calculate_cost_preview(
            model_id=request.aimodel_id,
            text_length=request.text_length
        )
        
        if "error" in result:
            return CostPreviewResponse(
                success=False,
                error=result["error"]
            )
        
        return CostPreviewResponse(
            success=True,
            model=result["model"],
            estimated_tokens=result["estimated_tokens"],
            estimated_points=result["estimated_points"],
            pricing_info=result["pricing_info"]
        )
        
    except Exception as e:
        logger.error(f"Cost preview error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"成本预览失败: {str(e)}"
        )


@router.post("/chat-with-article-stream")
async def chat_with_article_stream(
    request: ArticleChatRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    与文章内容进行流式聊天
    支持SSE (Server-Sent Events) 流式响应
    """
    current_user, access_token = user_info
    
    async def generate_sse_stream():
        try:
            # 1. 获取文章内容
            article = await material_service.get_article(current_user.id, request.article_id, access_token)
            if not article:
                error_data = {
                    "event": "error",
                    "message": "文章不存在或无权访问"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return
            
            # 2. 获取文章的所有分段
            segments, _ = await material_service.get_article_segments(
                current_user.id, 
                request.article_id, 
                page=1, 
                page_size=1000,  # 获取所有分段
                access_token=access_token
            )
            
            # 3. 构建包含完整文章内容的系统提示词
            article_content = ""
            if segments:
                article_content = "\n".join([segment.original_text for segment in segments])
            else:
                article_content = article.content if article else ""
            
            system_prompt = f"""你是一个专业的文章阅读助手。用户正在阅读以下文章，请根据文章内容回答用户的问题。

文章标题：{article.title if article else '无标题'}

文章内容：
{article_content}

请基于这篇文章的内容来回答用户的问题。如果用户的问题与文章内容无关，请礼貌地提醒用户你主要是帮助理解这篇文章的内容。"""
            
            # 4. 获取用户订阅级别
            user_subscription = "free"  # 默认值
            # TODO: 从用户服务获取实际订阅信息
            
            # 5. 使用流式聊天服务
            async for chunk in enhanced_ai_service.chat_completion_with_points_stream(
                user_id=current_user.id,
                user_subscription=user_subscription,
                model_id=request.aimodel_id,
                message=request.message,
                system_prompt=system_prompt,
                conversation_history=request.conversation_history,
                auto_charge=request.auto_charge
            ):
                # 将每个chunk包装为SSE格式
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"Article chat stream error: {e}", user_id=current_user.id)
            error_data = {
                "event": "error",
                "message": f"文章聊天失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.post("/chat-with-segments-stream")
async def chat_with_segments_stream(
    request: SegmentsChatRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    与选择的段落进行流式聊天
    支持SSE (Server-Sent Events) 流式响应
    """
    current_user, access_token = user_info
    
    async def generate_sse_stream():
        try:
            # 1. 获取文章内容
            article = await material_service.get_article(current_user.id, request.article_id, access_token)
            if not article:
                error_data = {
                    "event": "error",
                    "message": "文章不存在或无权访问"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return
            
            # 2. 获取文章的所有段落
            segments, _ = await material_service.get_article_segments(
                current_user.id, 
                request.article_id, 
                page=1, 
                page_size=1000,  # 获取所有段落
                access_token=access_token
            )
            
            # 3. 根据segment_ids筛选指定的段落
            segments_content = []
            segments_dict = {str(i): segment for i, segment in enumerate(segments)}
            
            for segment_id in request.segment_ids:
                try:
                    # 先尝试按索引查找
                    segment_index = int(segment_id)
                    if segment_index < len(segments):
                        segment = segments[segment_index]
                        segments_content.append(f"段落 {segment_id}: {segment.original_text}")
                    else:
                        # 如果索引超出范围，尝试按UUID查找
                        segment = next((s for s in segments if str(s.id) == segment_id), None)
                        if segment:
                            segments_content.append(f"段落 {segment_id}: {segment.original_text}")
                        else:
                            logger.warning(f"段落 {segment_id} 不存在")
                except (ValueError, TypeError):
                    # 如果不是数字，尝试按UUID查找
                    segment = next((s for s in segments if str(s.id) == segment_id), None)
                    if segment:
                        segments_content.append(f"段落 {segment_id}: {segment.original_text}")
                    else:
                        logger.warning(f"段落 {segment_id} 不存在")
            
            if not segments_content:
                error_data = {
                    "event": "error",
                    "message": "指定的段落不存在或无权访问"
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                return
            
            # 4. 构建包含选择段落内容的系统提示词
            selected_text = "\n\n".join(segments_content)
            
            system_prompt = f"""你是一个专业的文章阅读助手。用户正在阅读文章《{article.title if article else '无标题'}》，并选择了以下段落进行讨论：

选择的段落：
{selected_text}

请基于这些选择的段落内容来回答用户的问题。如果用户的问题与选择的段落内容无关，请礼貌地提醒用户你主要是帮助理解这些选择的段落内容。"""
            
            # 5. 获取用户订阅级别
            user_subscription = "free"  # 默认值
            # TODO: 从用户服务获取实际订阅信息
            
            # 6. 使用流式聊天服务
            async for chunk in enhanced_ai_service.chat_completion_with_points_stream(
                user_id=current_user.id,
                user_subscription=user_subscription,
                model_id=request.aimodel_id,
                message=request.message,
                system_prompt=system_prompt,
                conversation_history=request.conversation_history,
                auto_charge=request.auto_charge
            ):
                # 将每个chunk包装为SSE格式
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            logger.error(f"Segments chat stream error: {e}", user_id=current_user.id)
            error_data = {
                "event": "error",
                "message": f"段落聊天失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_sse_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.post("/reload-config")
async def reload_models_config(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    重新加载模型配置
    注意：这个端点应该只对管理员开放
    """
    current_user, access_token = user_info
    try:
        # TODO: 添加管理员权限检查
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="权限不足")
        
        enhanced_ai_service.reload_models_config()
        
        return {
            "success": True,
            "message": "模型配置已重新加载",
            "timestamp": "2025-01-25T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Reload config error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载配置失败: {str(e)}"
        )


# DeepSeek 测试相关模型
class DeepSeekTestRequest(BaseModel):
    aimodel_id: str = Field(default="deepseek-chat", description="要测试的DeepSeek模型ID")
    test_message: str = Field(default="请用中文介绍一下你自己，并展示你的代码能力", description="测试消息")
    auto_charge: bool = Field(True, description="是否自动扣费")


class DeepSeekTestResponse(BaseModel):
    success: bool
    message: str
    aimodel_info: Optional[Dict[str, Any]] = None
    test_result: Optional[Dict[str, Any]] = None
    points_transaction: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/test-deepseek", response_model=DeepSeekTestResponse)
async def test_deepseek_model(
    request: DeepSeekTestRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    测试DeepSeek模型接口
    支持用户认证、积分扣费，专门用于测试DeepSeek模型是否正常工作
    """
    current_user, access_token = user_info
    try:
        logger.info(f"User {current_user.id} testing DeepSeek model: {request.aimodel_id}")
        
        # 添加调试信息：检查用户积分
        from ....services.user_service import user_service
        user_profile = await user_service.get_user_profile(current_user.id)
        logger.info(f"用户积分检查 - 用户ID: {current_user.id}, 当前积分: {user_profile.get('points', 0) if user_profile else 'NO_PROFILE'}")
        
        # 验证模型ID是否为DeepSeek模型
        if not request.aimodel_id.startswith("deepseek"):
            # 如果不是deepseek开头，尝试补全
            if request.aimodel_id in ["chat", "coder"]:
                request.aimodel_id = f"deepseek-{request.aimodel_id}"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"只支持测试DeepSeek模型。支持的模型：deepseek-chat, deepseek-coder"
                )
        
        # 获取用户订阅级别
        user_subscription = "free"  # 默认值
        # TODO: 从用户服务获取实际订阅信息
        
        # 构建测试消息
        system_prompt = "你是DeepSeek AI助手。请用中文回答，并在回答中简要展示你的能力特点。"
        
        # 根据模型类型调整测试消息
        if "coder" in request.aimodel_id:
            test_message = request.test_message + "\n\n另外，请写一个简单的Python函数示例。"
        else:
            test_message = request.test_message
        
        # 调用增强AI服务进行测试
        result = await enhanced_ai_service.chat_completion_with_points(
            user_id=current_user.id,
            user_subscription=user_subscription,
            model_id=request.aimodel_id,
            message=test_message,
            system_prompt=system_prompt,
            conversation_history=None,
            auto_charge=request.auto_charge
        )
        
        if result.get("success"):
            return DeepSeekTestResponse(
                success=True,
                message=f"✅ DeepSeek模型 {request.aimodel_id} 测试成功！",
                aimodel_info={
                    "model_id": request.aimodel_id,
                    "provider": "openrouter",
                    "model_key": f"deepseek/{request.aimodel_id.replace('deepseek-', '')}",
                    "test_message": test_message
                },
                test_result={
                    "response": result.get("content", ""),
                    "response_length": len(result.get("content", "")),
                    "usage": result.get("usage"),
                    "model": result.get("model")
                },
                points_transaction=result.get("points_transaction")
            )
        else:
            return DeepSeekTestResponse(
                success=False,
                message=f"❌ DeepSeek模型 {request.aimodel_id} 测试失败",
                error=result.get("error", "未知错误"),
                aimodel_info={
                    "model_id": request.aimodel_id,
                    "test_message": test_message
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"DeepSeek test error: {e}", user_id=current_user.id)
        return DeepSeekTestResponse(
            success=False,
            message="❌ 测试过程中发生错误",
            error=str(e)
        )


@router.get("/debug-user-points")
async def debug_user_points(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    调试用户积分状态
    """
    current_user, access_token = user_info
    try:
        from ....services.user_service import user_service
        from ....services.points_service import points_service
        
        # 从多个来源获取用户积分信息
        user_profile = await user_service.get_user_profile(current_user.id)
        points_balance = await points_service.get_user_balance(current_user.id)
        
        return {
            "success": True,
            "user_id": current_user.id,
            "debug_info": {
                "user_profile_points": user_profile.get("points") if user_profile else None,
                "points_balance_total": points_balance.total_points if points_balance else None,
                "user_profile_exists": user_profile is not None,
                "points_balance_exists": points_balance is not None,
                "user_profile_data": user_profile,
                "points_balance_data": points_balance.dict() if points_balance else None
            }
        }
        
    except Exception as e:
        logger.error(f"Debug user points error: {e}", user_id=current_user.id)
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/my-transactions")
async def get_my_transactions(
    limit: int = Query(10, description="返回记录数量", ge=1, le=100),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取当前用户的积分交易历史
    """
    current_user, access_token = user_info
    try:
        from ....services.points_service import points_service
        
        # 获取用户的交易记录
        response = points_service.supabase.table("user_point_transactions").select("*").eq("user_id", current_user.id).order("created_at", desc=True).limit(limit).execute()
        
        transactions = response.data if response.data else []
        
        return {
            "success": True,
            "user_id": current_user.id,
            "transactions": transactions,
            "total_count": len(transactions)
        }
        
    except Exception as e:
        logger.error(f"Get transactions error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取交易历史失败: {str(e)}"
        )


@router.get("/deepseek-models")
async def get_deepseek_models(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取可用的DeepSeek模型列表
    """
    current_user, access_token = user_info
    try:
        # 获取用户订阅级别
        user_subscription = "free"
        
        # 获取所有可用模型
        all_models = await enhanced_ai_service.get_available_models(
            user_subscription=user_subscription
        )
        
        # 筛选DeepSeek模型
        deepseek_models = [
            model for model in all_models 
            if model.get("id", "").startswith("deepseek")
        ]
        
        return {
            "success": True,
            "deepseek_models": deepseek_models,
            "total_count": len(deepseek_models),
            "available_count": sum(1 for model in deepseek_models if model.get("available", False)),
            "user_tier": user_subscription
        }
        
    except Exception as e:
        logger.error(f"Get DeepSeek models error: {e}", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取DeepSeek模型列表失败: {str(e)}"
        )


@router.get("/health")
async def ai_enhanced_health_check(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    增强AI服务健康检查
    """
    current_user, access_token = user_info
    try:
        # 获取可用模型数量作为健康指标
        models = await enhanced_ai_service.get_available_models("enterprise")  # 获取所有模型
        available_count = sum(1 for model in models if model.get("available", False))
        total_count = len(models)
        
        status_text = "healthy" if available_count > 0 else "no_models"
        
        return {
            "status": status_text,
            "available_models": available_count,
            "total_models": total_count,
            "health_ratio": available_count / total_count if total_count > 0 else 0,
            "timestamp": "2025-01-25T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"AI enhanced health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-01-25T00:00:00Z"
        }


# 全局文章讲解相关模型
class GlobalArticleExplanationRequest(BaseModel):
    article_id: str = Field(..., description="文章ID")
    aimodel_id: str = Field("deepseek-chat-v3", description="模型ID")
    force_regenerate: bool = Field(False, description="强制重新生成已有讲解")
    auto_charge: bool = Field(True, description="是否自动扣费")


class GlobalArticleExplanationResponse(BaseModel):
    success: bool
    task_id: str
    message: str
    article_id: str
    aimodel_id: str


class BatchTranslateRequest(BaseModel):
    paragraphs: List[str] = Field(..., description="要翻译的段落列表", max_items=10)
    source_lang: str = Field(default="English", description="源语言")
    target_lang: str = Field(default="Chinese", description="目标语言")
    aimodel_id: str = Field(default="gemini-2.0-flash-001", description="AI模型ID")
    auto_charge: bool = Field(default=True, description="是否自动扣费")


class BatchTranslateResponse(BaseModel):
    success: bool
    translations: Optional[List[str]] = None
    error: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    points_transaction: Optional[Dict[str, Any]] = None


# @router.post("/batch-translate", response_model=BatchTranslateResponse)
# async def batch_translate(
#     request: BatchTranslateRequest,
#     user_info: tuple = Depends(get_current_user_with_token)
# ):
#     """
#     批量翻译段落
#     使用AI模型一次性翻译多个段落（最多10个）
#     
#     注释：此功能已迁移到 Node.js API，请使用 /api/ai/batch-translate 端点
#     """
#     current_user, access_token = user_info
#     
#     try:
#         # 验证段落数量
#         if len(request.paragraphs) > 10:
#             return BatchTranslateResponse(
#                 success=False,
#                 error="每次最多翻译10个段落"
#             )
#         
#         if not request.paragraphs:
#             return BatchTranslateResponse(
#                 success=False,
#                 error="请提供要翻译的段落"
#             )
#         
#         # 获取用户语言设置
#         user_profile = await user_service.get_user_profile(current_user.id)
#         
#         # 构建系统提示词
#         system_prompt = f"""You are a professional translator. Your task is to translate the following paragraphs from {request.source_lang} to {request.target_lang}.

# **IMPORTANT**: You must return EXACTLY a JSON array with the same number of translated paragraphs as the input. Each translated paragraph should correspond to the input paragraph at the same index.

# Example:
# Input: ["Hello world", "How are you?"]
# Output: ["你好世界", "你好吗？"]

# Rules:
# 1. Maintain the original meaning and tone
# 2. Keep the same paragraph structure
# 3. Return ONLY the JSON array, no other text
# 4. The number of output items MUST equal the number of input items
# 5. Empty paragraphs should be translated as empty strings
# """

#         # 构建用户消息
#         user_message = f"Translate these {len(request.paragraphs)} paragraphs:\n{json.dumps(request.paragraphs, ensure_ascii=False)}"
        
#         # 调用AI服务
#         result = await enhanced_ai_service.chat_completion_with_points(
#             user_id=current_user.id,
#             user_subscription=user_profile.get("plan_type", "free") if user_profile else "free",
#             model_id=request.aimodel_id,
#             message=user_message,
#             system_prompt=system_prompt,
#             auto_charge=request.auto_charge,
#         )
        
#         if not result['success']:
#             return BatchTranslateResponse(
#                 success=False,
#                 error=result.get('error', '翻译失败')
#             )
        
#         # 解析AI响应
#         ai_response = result.get('content', '')
        
#         # 尝试解析JSON数组
#         translations = []
#         try:
#             # 尝试直接解析
#             parsed = json.loads(ai_response.strip())
#             if isinstance(parsed, list):
#                 translations = parsed
#             else:
#                 raise ValueError("响应不是数组格式")
#         except:
#             # 尝试提取JSON数组
#             import re
#             array_match = re.search(r'\[.*?\]', ai_response, re.DOTALL)
#             if array_match:
#                 try:
#                     translations = json.loads(array_match.group(0))
#                 except:
#                     pass
        
#         # 验证翻译数量
#         if len(translations) != len(request.paragraphs):
#             logger.warning(
#                 f"Translation count mismatch",
#                 requested=len(request.paragraphs),
#                 received=len(translations),
#                 ai_response=ai_response
#             )
#             # 尝试补齐或截断
#             if len(translations) < len(request.paragraphs):
#                 # 补齐缺失的翻译（使用原文）
#                 translations.extend(request.paragraphs[len(translations):])
#             else:
#                 # 截断多余的翻译
#                 translations = translations[:len(request.paragraphs)]
        
#         return BatchTranslateResponse(
#             success=True,
#             translations=translations,
#             usage=result.get('usage'),
#             points_transaction=result.get('points_transaction')
#         )
        
#     except Exception as e:
#         logger.error(
#             f"Batch translation error",
#             user_id=current_user.id,
#             error=str(e),
#             exc_info=True
#         )
#         return BatchTranslateResponse(
#             success=False,
#             error=f"批量翻译失败: {str(e)}"
#         )

