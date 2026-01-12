"""
翻译 API 端点
"""

from fastapi import APIRouter, Depends, HTTPException
import logging

from ....services.enhanced_ai_service import enhanced_ai_service
from ....core.dependencies import get_current_user_with_token
from ....schemas.translation_schemas import TranslationRequest, TranslationResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/translate", response_model=TranslationResponse)
async def translate_text(
    request: TranslationRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    文本翻译API
    
    支持多语言翻译，使用阿里通义千问翻译模型
    每1000token消耗2积分
    """
    current_user, access_token = user_info
    try:
        # 获取用户订阅级别
        user_subscription = "free"  # 默认值
        # TODO: 从用户服务获取实际订阅信息
        
        # 调用翻译服务
        result = await enhanced_ai_service.translation_with_points(
            user_id=current_user.id,
            user_subscription=user_subscription,
            content=request.content,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            auto_charge=request.auto_charge,
            model_id="qwen-mt-turbo"
        )
        
        # 构建响应
        response = TranslationResponse(
            success=result["success"],
            translated_text=result.get("translated_text"),
            source_lang=result.get("source_lang"),
            target_lang=result.get("target_lang"),
            tokens_used=result.get("tokens_used"),
            points_consumed=result.get("points_consumed"),
            current_points=result.get("current_points"),
            error=result.get("error"),
            message=result.get("message")
        )
        
        # 如果翻译失败，返回HTTP错误
        if not result["success"]:
            error_code = result.get("error", "unknown_error")
            error_message = result.get("message", "翻译失败")
            
            # 根据错误类型设置不同的HTTP状态码
            if error_code in ["insufficient_points", "insufficient_points_final"]:
                raise HTTPException(status_code=402, detail=error_message)
            elif error_code == "model_access_denied":
                raise HTTPException(status_code=403, detail=error_message)
            elif error_code in ["model_not_found", "client_unavailable"]:
                raise HTTPException(status_code=503, detail=error_message)
            else:
                raise HTTPException(status_code=500, detail=error_message)
        
        return response
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"Translation API error: {e}")
        raise HTTPException(status_code=500, detail=f"翻译服务错误: {str(e)}")


@router.get("/languages")
async def get_supported_languages():
    """
    获取支持的翻译语言列表
    """
    return {
        "supported_languages": [
            {"code": "Chinese", "name": "中文", "display_name": "中文"},
            {"code": "English", "name": "English", "display_name": "英文"},
            {"code": "Japanese", "name": "日本語", "display_name": "日文"},
            {"code": "Korean", "name": "한국어", "display_name": "韩文"},
            {"code": "French", "name": "Français", "display_name": "法文"},
            {"code": "German", "name": "Deutsch", "display_name": "德文"},
            {"code": "Spanish", "name": "Español", "display_name": "西班牙文"},
            {"code": "Italian", "name": "Italiano", "display_name": "意大利文"},
            {"code": "Portuguese", "name": "Português", "display_name": "葡萄牙文"},
            {"code": "Russian", "name": "Русский", "display_name": "俄文"},
            {"code": "Arabic", "name": "العربية", "display_name": "阿拉伯文"},
            {"code": "Hindi", "name": "हिन्दी", "display_name": "印地文"},
            {"code": "Thai", "name": "ไทย", "display_name": "泰文"},
            {"code": "Vietnamese", "name": "Tiếng Việt", "display_name": "越南文"},
            {"code": "Danish", "name": "Dansk", "display_name": "丹麦语"},
            {"code": "Finnish", "name": "Suomi", "display_name": "芬兰语"}
        ]
    } 