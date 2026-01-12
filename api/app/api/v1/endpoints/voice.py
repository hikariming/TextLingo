from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
from typing import Dict, Any
import logging
import io

from app.schemas.voice import (
    TextToSpeechRequest,
    TextToSpeechResponse,
    VoicesResponse
)
from app.services.voice_service import voice_service
from app.core.dependencies import get_current_user, get_current_user_with_token
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/text-to-speech", response_class=StreamingResponse)
async def text_to_speech(
    request: TextToSpeechRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    文本转语音API
    
    将输入的文本转换为语音并返回音频流
    """
    current_user, access_token = user_info
    try:
        logger.info(f"用户 {current_user.email} 请求文本转语音: {request.text[:50]}...")
        
        # 调用语音服务（现在是异步的）
        result = await voice_service.text_to_speech(
            text=request.text,
            user_id=current_user.id,
            voice_id=request.voice_id,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
            sample_rate=request.sample_rate,
            bitrate=request.bitrate,
            audio_format=request.audio_format,
            auto_charge=True,
            access_token=access_token,
            language_boost=request.language_boost
        )
        
        if not result["success"]:
            # 根据错误类型返回不同的HTTP状态码
            if result["error"] == "insufficient_points":
                raise HTTPException(
                    status_code=402,
                    detail={
                        "message": result["message"],
                        "current_points": result.get("current_points", 0),
                        "required_points": result.get("required_points", 0)
                    }
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=result["message"]
                )
        
        # 获取音频数据
        audio_data = result["audio_data"]
        
        # 创建音频流
        audio_stream = io.BytesIO(audio_data)
        
        # 根据格式设置MIME类型
        mime_type = f"audio/{request.audio_format}"
        if request.audio_format == "mp3":
            mime_type = "audio/mpeg"
        
        # 在响应头中包含积分信息
        headers = {
            "Content-Disposition": f"attachment; filename=tts_audio.{request.audio_format}",
            "Content-Length": str(len(audio_data))
        }
        
        # 如果有积分交易信息，添加到响应头
        if result.get("points_transaction"):
            headers["X-Points-Consumed"] = str(result["points_transaction"]["points_consumed"])
            headers["X-Points-Remaining"] = str(result["points_transaction"]["points_after"])
        
        return StreamingResponse(
            audio_stream,
            media_type=mime_type,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文本转语音API错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="服务器内部错误"
        )


@router.post("/text-to-speech-url", response_model=TextToSpeechResponse)
async def text_to_speech_url(
    request: TextToSpeechRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    文本转语音API（返回URL方式）
    
    将输入的文本转换为语音并返回结果信息
    """
    current_user, access_token = user_info
    try:
        logger.info(f"用户 {current_user.email} 请求文本转语音URL: {request.text[:50]}...")
        
        # 调用语音服务
        result = await voice_service.text_to_speech(
            text=request.text,
            user_id=current_user.id,
            voice_id=request.voice_id,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
            sample_rate=request.sample_rate,
            bitrate=request.bitrate,
            audio_format=request.audio_format,
            auto_charge=True,
            access_token=access_token,
            language_boost=request.language_boost
        )
        
        if not result["success"]:
            return TextToSpeechResponse(
                success=False,
                message=result["message"]
            )
        
        # 这里可以将音频保存到临时文件或云存储，然后返回URL
        # 为了简化，这里直接返回成功信息
        points_info = ""
        if result.get("points_transaction"):
            points_info = f" (消耗积分: {result['points_transaction']['points_consumed']})"
        
        return TextToSpeechResponse(
            success=True,
            message=f"语音转换成功{points_info}",
            audio_url=None  # 在实际应用中，这里应该是音频文件的URL
        )
        
    except Exception as e:
        logger.error(f"文本转语音URL API错误: {str(e)}")
        return TextToSpeechResponse(
            success=False,
            message="服务器内部错误"
        )


@router.get("/voices", response_model=VoicesResponse)
async def get_available_voices(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取可用的声音列表
    
    返回所有可用的语音选项
    """
    current_user, access_token = user_info
    try:
        logger.info(f"用户 {current_user.email} 请求可用声音列表")
        
        voices_data = voice_service.get_available_voices()
        
        return VoicesResponse(**voices_data)
        
    except Exception as e:
        logger.error(f"获取声音列表API错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="获取声音列表失败"
        )


@router.get("/language-boost")
async def get_language_boost_options(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    获取支持的语言增强选项
    
    返回所有支持的语言增强选项
    """
    current_user, access_token = user_info
    try:
        logger.info(f"用户 {current_user.email} 请求语言增强选项")
        
        language_boost_data = voice_service.get_supported_language_boost()
        
        return language_boost_data
        
    except Exception as e:
        logger.error(f"获取语言增强选项API错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="获取语言增强选项失败"
        )


@router.get("/voices/test")
async def test_voice_service(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    测试语音服务配置
    
    检查Minimax API配置是否正确
    """
    current_user, access_token = user_info
    try:
        logger.info(f"用户 {current_user.email} 测试语音服务")
        
        # 测试基本配置
        has_api_key = bool(voice_service.api_key)
        has_group_id = bool(voice_service.group_id)
        
        return {
            "success": has_api_key and has_group_id,
            "message": "语音服务配置检查完成",
            "details": {
                "has_api_key": has_api_key,
                "has_group_id": has_group_id,
                "service_url": voice_service.base_url
            }
        }
        
    except Exception as e:
        logger.error(f"测试语音服务API错误: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="测试语音服务失败"
        ) 