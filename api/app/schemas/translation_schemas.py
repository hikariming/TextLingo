"""
翻译相关的数据模式
"""

from pydantic import BaseModel, Field
from typing import Optional


class TranslationRequest(BaseModel):
    """翻译请求模型"""
    content: str = Field(..., description="要翻译的文本内容", min_length=1, max_length=2000)
    source_lang: str = Field(..., description="源语言，如：Chinese, English, Japanese")
    target_lang: str = Field(..., description="目标语言，如：Chinese, English, Japanese")
    auto_charge: bool = Field(default=True, description="是否自动扣费")


class TranslationResponse(BaseModel):
    """翻译响应模型"""
    success: bool = Field(..., description="翻译是否成功")
    translated_text: Optional[str] = Field(None, description="翻译结果")
    source_lang: Optional[str] = Field(None, description="识别的源语言")
    target_lang: Optional[str] = Field(None, description="目标语言")
    tokens_used: Optional[int] = Field(None, description="消耗的token数量")
    points_consumed: Optional[int] = Field(None, description="消耗的积分")
    current_points: Optional[int] = Field(None, description="用户当前积分")
    error: Optional[str] = Field(None, description="错误类型")
    message: Optional[str] = Field(None, description="错误或成功消息") 