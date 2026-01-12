from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel
from app.services.activation_code_service import ActivationCodeService
from app.core.dependencies import get_current_user, get_current_user_with_token

router = APIRouter()

# Pydantic模型
class UseActivationCodeRequest(BaseModel):
    code: str

# 删除了CreateActivationCodesRequest和ActivationCodeResponse模型

@router.post("/use", response_model=dict)
async def use_activation_code(
    request: UseActivationCodeRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """使用激活码 - 有速率限制"""
    from app.core.rate_limiter import rate_limiter
    
    current_user, access_token = user_info
    user_id = current_user.id
    
    # 速率限制：每个用户每小时最多5次使用请求
    is_allowed, remaining = rate_limiter.is_allowed(
        key=f"use_activation:{user_id}",
        max_requests=5,
        window_seconds=3600  # 1小时
    )
    
    if not is_allowed:
        reset_time = rate_limiter.get_reset_time(f"use_activation:{user_id}", 3600)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="使用激活码过于频繁，请稍后再试",
            headers={
                "X-RateLimit-Limit": "5",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_time)
            }
        )
    
    service = ActivationCodeService(access_token)
    result = await service.use_activation_code(current_user.id, request.code)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=result["error"]
        )
    
    # 添加速率限制信息到响应
    result["rate_limit"] = {
        "remaining": remaining,
        "reset_time": rate_limiter.get_reset_time(f"use_activation:{user_id}", 3600)
    }
    
    return result

# 创建激活码接口已删除 - 安全考虑

# 管理员接口已移除 - 安全考虑，使用脚本直接管理
# GET /list - 获取激活码列表 (已移除)  
# GET /stats - 获取统计信息 (已移除)

@router.get("/history", response_model=dict)
async def get_user_activation_history(user_info: tuple = Depends(get_current_user_with_token)):
    """获取用户激活码使用历史"""
    current_user, access_token = user_info
    service = ActivationCodeService(access_token)
    result = await service.get_user_activation_history(current_user.id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )
    
    return result

# validate接口已移除 - 安全考虑，防止暴力破解探测激活码