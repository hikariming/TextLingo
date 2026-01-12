from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from pydantic import BaseModel
from app.services.subscription_service import SubscriptionService
from app.core.dependencies import get_current_user

router = APIRouter()

# Pydantic模型
class SubscriptionCreateRequest(BaseModel):
    plan_type: str
    payment_method: str = "activation_code"

@router.get("/current", response_model=dict)
async def get_current_subscription(current_user = Depends(get_current_user)):
    """获取当前用户订阅"""
    service = SubscriptionService()
    subscription = await service.get_user_subscription(current_user.id)
    
    if not subscription:
        return {
            "plan_type": "free", 
            "plan_name": "Free Plan",
            "status": "active",
            "priority": 0
        }
    
    return subscription

@router.get("/plans", response_model=dict)
async def get_subscription_plans():
    """获取所有订阅计划"""
    service = SubscriptionService()
    plans = await service.get_subscription_plans()
    return {"plans": plans}

@router.post("/subscribe", response_model=dict)
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user = Depends(get_current_user)
):
    """创建订阅"""
    service = SubscriptionService()
    result = await service.create_subscription(
        current_user.id, 
        request.plan_type,
        request.payment_method
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=result["error"]
        )
    
    return result

@router.get("/history", response_model=dict)
async def get_subscription_history(current_user = Depends(get_current_user)):
    """获取订阅历史"""
    service = SubscriptionService()
    
    try:
        response = service.supabase.from_("user_subscriptions")\
            .select("*")\
            .eq("user_id", current_user.id)\
            .order("created_at", desc=True)\
            .execute()
        
        return {"subscriptions": response.data or []}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription history"
        )