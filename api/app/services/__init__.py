"""
服务模块
"""

from .ai_service import ai_service, AIService
from .auth_service import AuthService
from .supabase_client import supabase_service, SupabaseService
from .points_service import points_service, PointsService
from .voice_service import voice_service, VoiceService

# 创建认证服务实例
auth_service = AuthService()

__all__ = [
    "ai_service",
    "AIService", 
    "auth_service",
    "AuthService",
    "supabase_service",
    "SupabaseService",
    "points_service",
    "PointsService",
    "voice_service",
    "VoiceService"
]
