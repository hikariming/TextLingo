from fastapi import APIRouter

from app.api.v1.endpoints import auth, ai, users, points, ai_enhanced, materials, dify, waitlist, voice, debug, rls_test, novels, translation, universal_assistant, activation_codes, subscriptions, novel_translation_config, revenuecat

api_router = APIRouter()

# 认证相关路由
api_router.include_router(auth.router, prefix="/auth", tags=["认证"])

# AI 助手相关路由
api_router.include_router(ai.router, prefix="/ai", tags=["AI助手"])

# 增强AI服务路由（新版本，集成积分和权限）
api_router.include_router(ai_enhanced.router, prefix="/ai-enhanced", tags=["增强AI服务"])

# 用户信息管理路由
api_router.include_router(users.router, prefix="/users", tags=["用户管理"])

# 积分管理路由
api_router.include_router(points.router, prefix="/points", tags=["积分管理"])



# 文章阅读材料管理路由
api_router.include_router(materials.router, prefix="/materials", tags=["文章阅读材料"])

# Dify AI 助手路由
api_router.include_router(dify.router, prefix="/dify", tags=["Dify AI助手"])

# 通用助手路由（支持多模型选择）
api_router.include_router(universal_assistant.router, prefix="/universal-assistant", tags=["通用助手"])

# Waitlist 路由（无需JWT鉴权）
api_router.include_router(waitlist.router, prefix="/waitlist", tags=["Waitlist"])

# 语音服务路由
api_router.include_router(voice.router, prefix="/voice", tags=["语音服务"])

# RLS调试路由
api_router.include_router(debug.debug_router, prefix="/debug", tags=["RLS调试"])

# RLS测试路由（用于测试和调试RLS权限配置）
api_router.include_router(rls_test.router, prefix="/rls-test", tags=["RLS权限测试"])

# 小说管理路由
api_router.include_router(novels.router, prefix="/novels", tags=["小说"])

# 小说翻译配置路由
api_router.include_router(novel_translation_config.router, prefix="/novel-translation-config", tags=["小说翻译配置"])

# 翻译服务路由
api_router.include_router(translation.router, prefix="/translation", tags=["翻译服务"])

# 激活码管理路由
api_router.include_router(activation_codes.router, prefix="/activation-codes", tags=["激活码管理"])

# 订阅管理路由
api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["订阅管理"])

# RevenueCat 集成路由
api_router.include_router(revenuecat.router, prefix="/revenuecat", tags=["RevenueCat集成"])
