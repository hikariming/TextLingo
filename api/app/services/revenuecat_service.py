"""
RevenueCat 集成服务
处理 RevenueCat 购买验证、用户同步等功能
"""

import os
import httpx
import structlog
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)


class RevenueCatService:
    """RevenueCat API 服务"""
    
    def __init__(self):
        self.secret_key = os.getenv("REVENUECAT_SECRET_API_KEY")
        self.base_url = "https://api.revenuecat.com/v1"
        self.webhook_secret = os.getenv("REVENUECAT_WEBHOOK_SECRET")
        
        if not self.secret_key:
            logger.warning("RevenueCat secret key not configured")
    
    async def get_subscriber_info(self, app_user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户订阅信息"""
        if not self.secret_key:
            logger.error("RevenueCat not configured")
            return None
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/subscribers/{app_user_id}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info("Retrieved subscriber info", user_id=app_user_id)
                    return data
                elif response.status_code == 404:
                    logger.info("Subscriber not found", user_id=app_user_id)
                    return None
                else:
                    logger.error(
                        "Failed to get subscriber info",
                        user_id=app_user_id,
                        status_code=response.status_code,
                        response=response.text
                    )
                    return None
                    
        except Exception as e:
            logger.error("Error getting subscriber info", user_id=app_user_id, error=str(e))
            return None
    
    async def create_subscriber(self, app_user_id: str, attributes: Optional[Dict] = None) -> bool:
        """创建或更新订阅者"""
        if not self.secret_key:
            logger.error("RevenueCat not configured")
            return False
            
        try:
            payload = {
                "attributes": attributes or {}
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/subscribers/{app_user_id}",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code in [200, 201]:
                    logger.info("Created/updated subscriber", user_id=app_user_id)
                    return True
                else:
                    logger.error(
                        "Failed to create subscriber",
                        user_id=app_user_id,
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False
                    
        except Exception as e:
            logger.error("Error creating subscriber", user_id=app_user_id, error=str(e))
            return False
    
    async def grant_entitlement(
        self, 
        app_user_id: str, 
        entitlement_id: str,
        duration_days: Optional[int] = None
    ) -> bool:
        """手动授予权益"""
        if not self.secret_key:
            logger.error("RevenueCat not configured")
            return False
            
        try:
            payload = {}
            if duration_days:
                # 计算过期时间
                import datetime
                expiry_date = datetime.datetime.now(timezone.utc) + datetime.timedelta(days=duration_days)
                payload["expiry_time"] = expiry_date.isoformat()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/subscribers/{app_user_id}/entitlements/{entitlement_id}/grant",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(
                        "Granted entitlement", 
                        user_id=app_user_id, 
                        entitlement=entitlement_id,
                        duration_days=duration_days
                    )
                    return True
                else:
                    logger.error(
                        "Failed to grant entitlement",
                        user_id=app_user_id,
                        entitlement=entitlement_id,
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error granting entitlement", 
                user_id=app_user_id, 
                entitlement=entitlement_id,
                error=str(e)
            )
            return False
    
    async def revoke_entitlement(self, app_user_id: str, entitlement_id: str) -> bool:
        """撤销权益"""
        if not self.secret_key:
            logger.error("RevenueCat not configured")
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/subscribers/{app_user_id}/entitlements/{entitlement_id}/revoke",
                    headers={
                        "Authorization": f"Bearer {self.secret_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    logger.info(
                        "Revoked entitlement", 
                        user_id=app_user_id, 
                        entitlement=entitlement_id
                    )
                    return True
                else:
                    logger.error(
                        "Failed to revoke entitlement",
                        user_id=app_user_id,
                        entitlement=entitlement_id,
                        status_code=response.status_code,
                        response=response.text
                    )
                    return False
                    
        except Exception as e:
            logger.error(
                "Error revoking entitlement", 
                user_id=app_user_id, 
                entitlement=entitlement_id,
                error=str(e)
            )
            return False
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """验证 RevenueCat webhook 签名"""
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured")
            return False
            
        try:
            import hmac
            import hashlib
            
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(f"sha256={expected_signature}", signature)
            
        except Exception as e:
            logger.error("Error verifying webhook signature", error=str(e))
            return False
    
    def parse_webhook_event(self, event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析 webhook 事件"""
        try:
            event_type = event_data.get("type")
            event_data_payload = event_data.get("event", {})
            
            # 提取关键信息
            app_user_id = event_data_payload.get("app_user_id")
            product_id = event_data_payload.get("product_id")
            entitlements = event_data_payload.get("entitlements", {})
            
            return {
                "event_type": event_type,
                "app_user_id": app_user_id,
                "product_id": product_id,
                "entitlements": entitlements,
                "raw_data": event_data_payload
            }
            
        except Exception as e:
            logger.error("Error parsing webhook event", error=str(e))
            return None
    
    def extract_subscription_info(self, subscriber_data: Dict[str, Any]) -> Dict[str, Any]:
        """从订阅者数据中提取关键信息"""
        try:
            subscriber = subscriber_data.get("subscriber", {})
            entitlements = subscriber.get("entitlements", {})
            
            # 检查活跃的权益
            active_entitlements = []
            subscription_status = "inactive"
            expiry_date = None
            
            for entitlement_id, entitlement_data in entitlements.items():
                if entitlement_data.get("is_active", False):
                    active_entitlements.append(entitlement_id)
                    
                    # 获取过期时间
                    expires_date = entitlement_data.get("expires_date")
                    if expires_date:
                        try:
                            parsed_date = datetime.fromisoformat(expires_date.replace('Z', '+00:00'))
                            if not expiry_date or parsed_date > expiry_date:
                                expiry_date = parsed_date
                        except ValueError:
                            pass
            
            if active_entitlements:
                subscription_status = "active"
            
            # 检查是否在试用期
            is_trial = any(
                entitlements.get(ent, {}).get("period_type") == "trial" 
                for ent in active_entitlements
            )
            
            return {
                "status": subscription_status,
                "active_entitlements": active_entitlements,
                "is_trial": is_trial,
                "expiry_date": expiry_date.isoformat() if expiry_date else None,
                "raw_subscriber_data": subscriber
            }
            
        except Exception as e:
            logger.error("Error extracting subscription info", error=str(e))
            return {
                "status": "error",
                "active_entitlements": [],
                "is_trial": False,
                "expiry_date": None
            }


# 创建全局实例
revenuecat_service = RevenueCatService()