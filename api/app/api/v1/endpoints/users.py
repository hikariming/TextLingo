from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.core.dependencies import get_current_user, get_current_user_with_token
from app.schemas.auth import UserResponse
from app.schemas.user import (
    UserCompleteProfile,
    UserProfileUpdate,
    UserSubscription,
    UserSubscriptionCreate,
    UserSubscriptionUpdate,
    AvatarUploadResponse,
    ProfileSetupRequest,
    ProfileSetupResponse,
    LingoCloudStatsResponse
)
from app.services.user_service import UserService

router = APIRouter()


@router.get("/profile", response_model=UserCompleteProfile)
async def get_current_user_profile(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """Get current user's complete profile, auto-create if not exists"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    profile = await user_service.get_user_profile(current_user.id)
    
    # get_user_profile method already includes auto-creation logic, if returns None it means creation also failed
    if not profile:
        raise HTTPException(status_code=500, detail="Unable to get or create user profile")
    
    return profile


@router.put("/profile", response_model=UserCompleteProfile)
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """Update current user's basic profile information"""
    try:
        current_user, access_token = user_info
        user_service = UserService(access_token=access_token)
        updated_profile = await user_service.update_user_profile(current_user.id, profile_data)
        return updated_profile
    except HTTPException:
        # Re-raise HTTP exceptions from the service layer
        raise
    except Exception as e:
        # Log the unexpected error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error updating profile for user {current_user.id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error while updating user profile: {str(e)}")


@router.post("/avatar", response_model=AvatarUploadResponse)
async def upload_user_avatar(
    file: UploadFile = File(...),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """上传用户头像"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    
    # 验证文件大小 (5MB限制)
    max_size = 5 * 1024 * 1024  # 5MB
    if file.size and file.size > max_size:
        raise HTTPException(status_code=400, detail="文件大小不能超过5MB")
    
    result = await user_service.upload_avatar(current_user.id, file)
    return result


@router.delete("/avatar")
async def delete_user_avatar(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """删除用户头像"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    result = await user_service.delete_avatar(current_user.id)
    return result


@router.get("/subscription", response_model=UserSubscription)
async def get_current_user_subscription(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取当前用户的订阅信息"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    subscription = await user_service.get_user_subscription(current_user.id)
    
    if not subscription:
        raise HTTPException(status_code=404, detail="没有找到订阅信息")
    
    return subscription


@router.post("/subscription", response_model=UserSubscription)
async def create_user_subscription(
    subscription_data: UserSubscriptionCreate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """创建用户订阅"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    new_subscription = await user_service.create_subscription(current_user.id, subscription_data)
    return new_subscription


@router.put("/subscription", response_model=UserSubscription)
async def update_user_subscription(
    subscription_data: UserSubscriptionUpdate,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """更新用户订阅"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    updated_subscription = await user_service.update_subscription(current_user.id, subscription_data)
    return updated_subscription


@router.delete("/subscription")
async def cancel_user_subscription(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """取消用户订阅"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    result = await user_service.cancel_subscription(current_user.id)
    return result


@router.post("/points")
async def update_user_points(
    points_change: int,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """更新用户积分"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    result = await user_service.update_user_points(current_user.id, points_change)
    return result


@router.get("/points")
async def get_user_points(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户当前积分，如果不存在则自动创建"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    profile = await user_service.get_user_profile(current_user.id)
    
    # get_user_profile 方法已经包含自动创建逻辑，如果返回None说明创建也失败了
    if not profile:
        raise HTTPException(status_code=500, detail="无法获取或创建用户信息")
    
    return {
        "user_id": current_user.id,
        "points": profile["points"],
        "role": profile["role"]
    }


@router.post("/profile/setup", response_model=ProfileSetupResponse)
async def complete_profile_setup(
    setup_data: ProfileSetupRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """Complete user initial setup (mainly for Google login users)"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    result = await user_service.complete_profile_setup(current_user.id, setup_data)
    return result


@router.get("/profile/setup-status")
async def get_profile_setup_status(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """Check if user has completed initial setup, auto-create if not exists"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    profile = await user_service.get_user_profile(current_user.id)
    
    # get_user_profile method already includes auto-creation logic, if returns None it means creation also failed
    if not profile:
        raise HTTPException(status_code=500, detail="Unable to get or create user profile")
    
    return {
        "user_id": current_user.id,
        "profile_setup_completed": profile.get("profile_setup_completed", False),
        "native_language": profile.get("native_language"),
        "learning_language": profile.get("learning_language"),
        "language_level": profile.get("language_level")
    }


@router.get("/lingocloud-stats", response_model=LingoCloudStatsResponse)
async def get_user_lingocloud_stats(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户LingoCloud综合统计信息"""
    current_user, access_token = user_info
    user_service = UserService(access_token=access_token)
    
    try:
        stats = await user_service.get_lingocloud_stats(current_user.id)
        return LingoCloudStatsResponse(
            success=True,
            message="获取统计信息成功",
            data=stats
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"获取统计信息失败: {str(e)}"
        ) 