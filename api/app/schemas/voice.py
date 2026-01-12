from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class TextToSpeechRequest(BaseModel):
    """文本转语音请求模型"""
    text: str = Field(..., description="要转换的文本", min_length=1, max_length=5000)
    voice_id: Optional[str] = Field(
        default="Chinese (Mandarin)_Radio_Host",
        description="声音ID"
    )
    speed: Optional[float] = Field(
        default=0.8,
        description="语速",
        ge=0.1,
        le=2.0
    )
    pitch: Optional[float] = Field(
        default=0,
        description="音调",
        ge=-1.0,
        le=1.0
    )
    volume: Optional[float] = Field(
        default=1.0,
        description="音量",
        ge=0.1,
        le=2.0
    )
    sample_rate: Optional[int] = Field(
        default=32000,
        description="采样率"
    )
    bitrate: Optional[int] = Field(
        default=128000,
        description="比特率"
    )
    audio_format: Optional[str] = Field(
        default="mp3",
        description="音频格式"
    )
    language_boost: Optional[str] = Field(
        default="auto",
        description="语言增强选项，增强对指定的小语种和方言的识别能力。支持: 'Chinese', 'Chinese,Yue', 'English', 'Arabic', 'Russian', 'Spanish', 'French', 'Portuguese', 'German', 'Turkish', 'Dutch', 'Ukrainian', 'Vietnamese', 'Indonesian', 'Japanese', 'Italian', 'Korean', 'Thai', 'Polish', 'Romanian', 'Greek', 'Czech', 'Finnish', 'Hindi', 'auto'"
    )


class VoiceInfo(BaseModel):
    """声音信息模型"""
    id: str = Field(..., description="声音ID")
    name: str = Field(..., description="声音名称")
    language: str = Field(..., description="语言代码")
    gender: str = Field(..., description="性别")


class VoicesResponse(BaseModel):
    """可用声音列表响应模型"""
    chinese_voices: list[VoiceInfo] = Field(..., description="中文声音列表")
    english_voices: list[VoiceInfo] = Field(..., description="英文声音列表")
    japanese_voices: list[VoiceInfo] = Field(..., description="日文声音列表")


class TextToSpeechResponse(BaseModel):
    """文本转语音响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    audio_url: Optional[str] = Field(None, description="音频下载URL（如果成功）") 