"""
AI 相关的 API 端点
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List, Dict, Any
import logging

from ....services.ai_service import ai_service
from ....core.dependencies import get_current_user
from ....schemas.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic 模型
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    provider: str = Field("gemini", description="AI 提供商")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="对话历史")

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., description="要分析的文本")
    analysis_type: str = Field("explain", description="分析类型: explain, translate, summarize")
    target_language: str = Field("zh", description="目标语言")
    provider: str = Field("gemini", description="AI 提供商")

class AIResponse(BaseModel):
    success: bool
    content: Optional[str] = None
    error: Optional[str] = None
    provider: str
    model: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


@router.post("/chat", response_model=AIResponse)
async def chat_completion(
    request: ChatRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    AI 聊天完成
    """
    try:
        # 验证提供商是否可用
        available_providers = ai_service.get_available_providers()
        if request.provider not in available_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Provider {request.provider} not available. Available: {available_providers}"
            )
        
        # 调用 AI 服务
        result = await ai_service.chat_completion(
            message=request.message,
            system_prompt=request.system_prompt,
            provider=request.provider,
            conversation_history=request.conversation_history
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Chat completion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=AIResponse)
async def analyze_text(
    request: TextAnalysisRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    文本分析
    """
    try:
        # 验证提供商是否可用
        available_providers = ai_service.get_available_providers()
        if request.provider not in available_providers:
            raise HTTPException(
                status_code=400,
                detail=f"Provider {request.provider} not available. Available: {available_providers}"
            )
        
        # 验证分析类型
        valid_types = ["explain", "translate", "summarize"]
        if request.analysis_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid analysis_type. Valid options: {valid_types}"
            )
        
        # 调用 AI 服务
        result = await ai_service.text_analysis(
            text=request.text,
            analysis_type=request.analysis_type,
            target_language=request.target_language,
            provider=request.provider
        )
        
        return AIResponse(**result)
        
    except Exception as e:
        logger.error(f"Text analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def get_providers(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    获取可用的 AI 提供商
    """
    try:
        providers = ai_service.get_available_providers()
        return {
            "success": True,
            "providers": providers,
            "default": "gemini" if "gemini" in providers else providers[0] if providers else None
        }
    except Exception as e:
        logger.error(f"Get providers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def ai_health_check():
    """
    AI 服务健康检查
    """
    try:
        providers = ai_service.get_available_providers()
        return {
            "status": "healthy" if providers else "no_providers",
            "available_providers": providers,
            "timestamp": "2025-01-25T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"AI health check error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": "2025-01-25T00:00:00Z"
        }
