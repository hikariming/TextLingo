"""
RevenueCat 集成 API endpoints
处理购买同步、webhook 等功能
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import Response
from typing import Dict, Any, Optional
import structlog
from datetime import datetime

from app.core.dependencies import get_current_user
from app.services.revenuecat_service import revenuecat_service
from app.services.subscription_service import subscription_service
from app.services.points_service import points_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/sync-purchase")
async def sync_revenuecat_purchase(
    purchase_data: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    同步 RevenueCat 购买到后端系统
    客户端购买成功后调用此接口
    """
    try:
        user_id = str(current_user.id)
        transaction_id = purchase_data.get("transaction_id")
        product_id = purchase_data.get("product_id")
        purchase_date = purchase_data.get("purchase_date")
        is_restore = purchase_data.get("is_restore", False)
        
        logger.info(
            "Syncing RevenueCat purchase",
            user_id=user_id,
            product_id=product_id,
            transaction_id=transaction_id,
            is_restore=is_restore
        )
        
        # 获取 RevenueCat 订阅者信息进行验证
        subscriber_info = await revenuecat_service.get_subscriber_info(user_id)
        if not subscriber_info:
            logger.warning("No subscriber info found", user_id=user_id)
            raise HTTPException(status_code=404, detail="Subscriber not found")
        
        # 提取订阅信息
        subscription_info = revenuecat_service.extract_subscription_info(subscriber_info)
        
        # 检查产品类型并处理
        if _is_subscription_product(product_id):
            # 处理订阅产品
            await _handle_subscription_purchase(
                user_id, product_id, subscription_info, transaction_id
            )
        elif _is_points_product(product_id):
            # 处理积分产品
            points_amount = _get_points_for_product(product_id)
            if points_amount > 0:
                await _handle_points_purchase(
                    user_id, product_id, points_amount, transaction_id
                )
        
        logger.info(
            "Purchase synced successfully",
            user_id=user_id,
            product_id=product_id
        )
        
        return {
            "success": True,
            "message": "Purchase synced successfully",
            "subscription_info": subscription_info
        }
        
    except Exception as e:
        logger.error("Error syncing purchase", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to sync purchase: {str(e)}")


@router.post("/webhook")
async def revenuecat_webhook(
    request: Request,
    x_revenuecat_signature: Optional[str] = Header(None)
):
    """
    RevenueCat Webhook 处理
    自动同步购买状态变化
    """
    try:
        # 获取原始请求体
        body = await request.body()
        
        # 验证签名（如果配置了）
        if x_revenuecat_signature:
            if not revenuecat_service.verify_webhook_signature(body, x_revenuecat_signature):
                logger.warning("Invalid webhook signature")
                raise HTTPException(status_code=400, detail="Invalid signature")
        
        # 解析事件数据
        event_data = await request.json()
        parsed_event = revenuecat_service.parse_webhook_event(event_data)
        
        if not parsed_event:
            raise HTTPException(status_code=400, detail="Invalid event data")
        
        event_type = parsed_event["event_type"]
        app_user_id = parsed_event["app_user_id"]
        
        logger.info(
            "Received RevenueCat webhook",
            event_type=event_type,
            user_id=app_user_id
        )
        
        # 根据事件类型处理
        if event_type in ["INITIAL_PURCHASE", "RENEWAL", "PRODUCT_CHANGE"]:
            await _handle_purchase_event(parsed_event)
        elif event_type in ["CANCELLATION", "EXPIRATION"]:
            await _handle_cancellation_event(parsed_event)
        elif event_type == "NON_RENEWING_PURCHASE":
            await _handle_points_purchase_event(parsed_event)
        
        return Response(content="OK", status_code=200)
        
    except Exception as e:
        logger.error("Error processing webhook", error=str(e))
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.get("/subscriber-info")
async def get_subscriber_info(current_user = Depends(get_current_user)):
    """获取用户的 RevenueCat 订阅信息"""
    try:
        user_id = str(current_user.id)
        
        # 获取 RevenueCat 订阅信息
        subscriber_info = await revenuecat_service.get_subscriber_info(user_id)
        
        if not subscriber_info:
            return {
                "found": False,
                "subscription_info": None
            }
        
        # 提取关键信息
        subscription_info = revenuecat_service.extract_subscription_info(subscriber_info)
        
        return {
            "found": True,
            "subscription_info": subscription_info
        }
        
    except Exception as e:
        logger.error("Error getting subscriber info", error=str(e), user_id=str(current_user.id))
        raise HTTPException(status_code=500, detail="Failed to get subscriber info")


async def _handle_subscription_purchase(
    user_id: str,
    product_id: str, 
    subscription_info: Dict[str, Any],
    transaction_id: Optional[str]
):
    """处理订阅购买"""
    try:
        # 更新用户订阅状态
        await subscription_service.update_subscription_from_revenuecat(
            user_id, subscription_info, transaction_id
        )
        
        logger.info(
            "Subscription purchase processed",
            user_id=user_id,
            product_id=product_id,
            status=subscription_info.get("status")
        )
        
    except Exception as e:
        logger.error("Error processing subscription purchase", error=str(e))
        raise


async def _handle_points_purchase(
    user_id: str,
    product_id: str,
    points_amount: int,
    transaction_id: Optional[str]
):
    """处理积分购买"""
    try:
        # 添加积分到用户账户
        await points_service.add_points(
            user_id,
            points_amount,
            f"RevenueCat purchase: {product_id}",
            transaction_id
        )
        
        logger.info(
            "Points purchase processed",
            user_id=user_id,
            product_id=product_id,
            points_amount=points_amount
        )
        
    except Exception as e:
        logger.error("Error processing points purchase", error=str(e))
        raise


async def _handle_purchase_event(parsed_event: Dict[str, Any]):
    """处理购买相关的 webhook 事件"""
    app_user_id = parsed_event["app_user_id"]
    product_id = parsed_event["product_id"]
    
    # 获取最新的订阅者信息
    subscriber_info = await revenuecat_service.get_subscriber_info(app_user_id)
    if subscriber_info:
        subscription_info = revenuecat_service.extract_subscription_info(subscriber_info)
        
        if _is_subscription_product(product_id):
            await _handle_subscription_purchase(app_user_id, product_id, subscription_info, None)
        elif _is_points_product(product_id):
            points_amount = _get_points_for_product(product_id)
            if points_amount > 0:
                await _handle_points_purchase(app_user_id, product_id, points_amount, None)


async def _handle_cancellation_event(parsed_event: Dict[str, Any]):
    """处理取消/过期事件"""
    app_user_id = parsed_event["app_user_id"]
    
    # 获取最新状态并更新
    subscriber_info = await revenuecat_service.get_subscriber_info(app_user_id)
    if subscriber_info:
        subscription_info = revenuecat_service.extract_subscription_info(subscriber_info)
        await subscription_service.update_subscription_from_revenuecat(
            app_user_id, subscription_info, None
        )


async def _handle_points_purchase_event(parsed_event: Dict[str, Any]):
    """处理积分购买事件"""
    app_user_id = parsed_event["app_user_id"]
    product_id = parsed_event["product_id"]
    
    points_amount = _get_points_for_product(product_id)
    if points_amount > 0:
        await _handle_points_purchase(app_user_id, product_id, points_amount, None)


def _is_subscription_product(product_id: str) -> bool:
    """检查是否为订阅产品"""
    subscription_products = [
        "com.textlingo.textlingoMobile.Monthly",
        "com.textlingo.textlingoMobile.Annual"
    ]
    return product_id in subscription_products


def _is_points_product(product_id: str) -> bool:
    """检查是否为积分产品"""
    points_products = [
        "textlingo_points_4500",
        "textlingo_points_9000",
        "textlingo_points_18000",
        "textlingo_points_36000"
    ]
    return product_id in points_products


def _get_points_for_product(product_id: str) -> int:
    """获取产品对应的积分数量"""
    points_mapping = {
        "textlingo_points_4500": 4500,
        "textlingo_points_9000": 9000,
        "textlingo_points_18000": 18000,
        "textlingo_points_36000": 36000
    }
    return points_mapping.get(product_id, 0)