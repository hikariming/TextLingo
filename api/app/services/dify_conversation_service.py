"""
Dify 会话管理服务 - 处理会话、消息和文件的数据库操作
"""

import json
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.services.supabase_client import supabase_service

logger = logging.getLogger(__name__)

@dataclass
class DifyConversation:
    id: str
    user_id: str
    flow_id: str
    dify_conversation_id: Optional[str]
    title: str
    model_config: Dict[str, Any]
    total_messages: int
    total_points_consumed: int
    is_archived: bool
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@dataclass
class DifyMessage:
    id: str
    conversation_id: str
    user_id: str
    role: str  # user 或 assistant
    content: str
    dify_message_id: Optional[str]
    dify_task_id: Optional[str]
    input_tokens: int
    output_tokens: int
    total_tokens: int
    points_consumed: int
    processing_time_ms: int
    metadata: Dict[str, Any]
    created_at: datetime

@dataclass
class DifyFile:
    id: str
    user_id: str
    message_id: Optional[str]
    dify_file_id: str
    filename: str
    file_size: int
    file_type: str
    content_type: str
    created_at: datetime

@dataclass
class DifyPointTransaction:
    id: str
    user_id: str
    conversation_id: str
    message_id: Optional[str]
    transaction_type: str  # deduct, refund, adjustment
    points_amount: int
    model_used: str
    usage_data: Optional[Dict[str, Any]]
    reason: str
    created_at: datetime

class DifyConversationService:
    """Dify 会话管理服务"""
    
    def __init__(self):
        self.supabase = supabase_service.get_client()
    
    def _get_user_client(self, access_token: str):
        """根据access_token获取用户客户端"""
        if not access_token:
            # 临时兼容处理：如果没有access_token，使用service client
            logger.warning("没有提供access_token，使用service client（临时兼容）")
            return self.supabase
        return supabase_service.get_user_client(access_token)
    
    async def create_conversation(
        self,
        user_id: str,
        model: str,
        access_token: str,
        flow_id: str = "universal-assistant",
        name: Optional[str] = None
    ) -> DifyConversation:
        """
        创建新的Dify会话
        
        Args:
            user_id: 用户ID
            model: 选择的模型
            flow_id: 流ID
            name: 会话名称（如果为空会自动生成）
            
        Returns:
            创建的会话对象
        """
        try:
            user_client = self._get_user_client(access_token)
            conversation_id = str(uuid.uuid4())
            
            # 如果没有提供名称，生成默认名称
            if not name:
                timestamp = datetime.now().strftime("%m-%d %H:%M")
                name = f"与{model}的对话 {timestamp}"
            
            conversation_data = {
                "id": conversation_id,
                "user_id": user_id,
                "flow_id": flow_id,
                "title": name,
                "model_config": {"selected_model": model},
                "total_messages": 0,
                "total_points_consumed": 0,
                "is_archived": False,
                "metadata": {},
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = user_client.from_("dify_conversations").insert(conversation_data).execute()
            
            if not result.data:
                raise Exception("会话创建失败")
            
            created_data = result.data[0]
            logger.info(f"成功创建Dify会话: {conversation_id} for user {user_id}")
            
            return DifyConversation(
                id=created_data["id"],
                user_id=created_data["user_id"],
                flow_id=created_data["flow_id"],
                dify_conversation_id=created_data.get("dify_conversation_id"),
                title=created_data["title"],
                model_config=created_data["model_config"],
                total_messages=created_data["total_messages"],
                total_points_consumed=created_data["total_points_consumed"],
                is_archived=created_data["is_archived"],
                metadata=created_data["metadata"],
                created_at=datetime.fromisoformat(created_data["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(created_data["updated_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"创建Dify会话失败: {e}")
            raise Exception(f"创建会话失败: {str(e)}")
    
    async def get_conversation(self, user_id: str, conversation_id: str, access_token: str) -> Optional[DifyConversation]:
        """
        获取用户的特定会话
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            
        Returns:
            会话对象或None
        """
        try:
            user_client = self._get_user_client(access_token)
            result = user_client.from_("dify_conversations").select("*").eq(
                "id", conversation_id
            ).eq(
                "user_id", user_id
            ).eq(
                "is_archived", False
            ).execute()
            
            if not result.data:
                return None
            
            data = result.data[0]
            return DifyConversation(
                id=data["id"],
                user_id=data["user_id"],
                flow_id=data["flow_id"],
                dify_conversation_id=data.get("dify_conversation_id"),
                title=data["title"],
                model_config=data["model_config"],
                total_messages=data["total_messages"],
                total_points_consumed=data["total_points_consumed"],
                is_archived=data["is_archived"],
                metadata=data["metadata"],
                created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
                updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"获取会话失败: {e}")
            return None
    
    async def get_user_conversations(
        self,
        user_id: str,
        access_token: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[DifyConversation]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            会话列表
        """
        try:
            user_client = self._get_user_client(access_token)
            result = user_client.from_("dify_conversations").select("*").eq(
                "user_id", user_id
            ).eq(
                "is_archived", False
            ).order(
                "updated_at", desc=True
            ).range(
                offset, offset + limit - 1
            ).execute()
            
            conversations = []
            for data in result.data:
                conversations.append(DifyConversation(
                    id=data["id"],
                    user_id=data["user_id"],
                    flow_id=data["flow_id"],
                    dify_conversation_id=data.get("dify_conversation_id"),
                    title=data["title"],
                    model_config=data["model_config"],
                    total_messages=data["total_messages"],
                    total_points_consumed=data["total_points_consumed"],
                    is_archived=data["is_archived"],
                    metadata=data["metadata"],
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00')),
                    updated_at=datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
                ))
            
            logger.info(f"获取用户 {user_id} 的 {len(conversations)} 个会话")
            return conversations
            
        except Exception as e:
            logger.error(f"获取会话列表失败: {e}")
            return []
    
    async def update_conversation_activity(self, conversation_id: str, access_token: Optional[str] = None) -> None:
        """
        更新会话的活动时间
        
        Args:
            conversation_id: 会话ID
        """
        try:
            self.supabase.from_("dify_conversations").update({
                "updated_at": datetime.now().isoformat()
            }).eq("id", conversation_id).execute()
            
        except Exception as e:
            logger.error(f"更新会话活动时间失败: {e}")
    
    async def update_conversation_dify_id(
        self, 
        conversation_id: str, 
        dify_conversation_id: str
    ) -> None:
        """
        更新会话的Dify会话ID
        
        Args:
            conversation_id: 本地会话ID
            dify_conversation_id: Dify平台的会话ID
        """
        try:
            self.supabase.from_("dify_conversations").update({
                "dify_conversation_id": dify_conversation_id,
                "updated_at": datetime.now().isoformat()
            }).eq("id", conversation_id).execute()
            
            logger.info(f"更新会话 {conversation_id} 的Dify ID: {dify_conversation_id}")
            
        except Exception as e:
            logger.error(f"更新会话Dify ID失败: {e}")
    
    async def delete_conversation(self, conversation_id: str) -> None:
        """
        删除会话（软删除，标记为archived）
        
        Args:
            conversation_id: 会话ID
        """
        try:
            self.supabase.from_("dify_conversations").update({
                "is_archived": True,
                "updated_at": datetime.now().isoformat()
            }).eq("id", conversation_id).execute()
            
            logger.info(f"成功删除会话: {conversation_id}")
            
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            raise Exception(f"删除会话失败: {str(e)}")
    
    async def save_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        access_token: Optional[str] = None,
        dify_message_id: Optional[str] = None,
        dify_task_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        points_consumed: int = 0,
        processing_time_ms: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DifyMessage:
        """
        保存消息到数据库
        
        Args:
            conversation_id: 会话ID
            user_id: 用户ID
            role: 角色（user/assistant）
            content: 消息内容
            model: 使用的模型
            files: 文件ID列表
            dify_message_id: Dify消息ID
            dify_task_id: Dify任务ID
            usage_data: 使用统计数据
            
        Returns:
            保存的消息对象
        """
        try:
            client = self._get_user_client(access_token) if access_token else self.supabase
            message_id = str(uuid.uuid4())
            
            message_data = {
                "id": message_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "dify_message_id": dify_message_id,
                "dify_task_id": dify_task_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "points_consumed": points_consumed,
                "processing_time_ms": processing_time_ms,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat()
            }
            
            result = client.from_("dify_messages").insert(message_data).execute()
            
            if not result.data:
                raise Exception("消息保存失败")
            
            created_data = result.data[0]
            
            logger.info(f"成功保存消息: {message_id} ({role}) in conversation {conversation_id}")
            
            return DifyMessage(
                id=created_data["id"],
                conversation_id=created_data["conversation_id"],
                user_id=created_data["user_id"],
                role=created_data["role"],
                content=created_data["content"],
                dify_message_id=created_data.get("dify_message_id"),
                dify_task_id=created_data.get("dify_task_id"),
                input_tokens=created_data["input_tokens"],
                output_tokens=created_data["output_tokens"],
                total_tokens=created_data["total_tokens"],
                points_consumed=created_data["points_consumed"],
                processing_time_ms=created_data["processing_time_ms"],
                metadata=created_data["metadata"],
                created_at=datetime.fromisoformat(created_data["created_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            raise Exception(f"保存消息失败: {str(e)}")
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[DifyMessage]:
        """
        获取会话的消息列表
        
        Args:
            conversation_id: 会话ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            消息列表
        """
        try:
            result = self.supabase.from_("dify_messages").select("*").eq(
                "conversation_id", conversation_id
            ).order(
                "created_at", desc=True
            ).range(
                offset, offset + limit - 1
            ).execute()
            
            messages = []
            for data in result.data:
                messages.append(DifyMessage(
                    id=data["id"],
                    conversation_id=data["conversation_id"],
                    user_id=data["user_id"],
                    role=data["role"],
                    content=data["content"],
                    dify_message_id=data.get("dify_message_id"),
                    dify_task_id=data.get("dify_task_id"),
                    input_tokens=data["input_tokens"],
                    output_tokens=data["output_tokens"],
                    total_tokens=data["total_tokens"],
                    points_consumed=data["points_consumed"],
                    processing_time_ms=data["processing_time_ms"],
                    metadata=data["metadata"],
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
                ))
            
            # 反转列表，使最早的消息在前面
            messages.reverse()
            
            logger.info(f"获取会话 {conversation_id} 的 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            logger.error(f"获取会话消息失败: {e}")
            return []
    
    async def save_file(
        self,
        user_id: str,
        dify_file_id: str,
        filename: str,
        file_size: int,
        content_type: str,
        message_id: Optional[str] = None
    ) -> DifyFile:
        """
        保存文件信息到数据库
        
        Args:
            user_id: 用户ID
            dify_file_id: Dify文件ID
            filename: 文件名
            file_size: 文件大小
            content_type: 文件类型
            message_id: 关联的消息ID
            
        Returns:
            保存的文件对象
        """
        try:
            file_id = str(uuid.uuid4())
            
            # 确定文件类型
            def determine_file_type(filename: str, content_type: str) -> str:
                if not filename:
                    return "document"
                    
                ext = filename.lower().split('.')[-1] if '.' in filename else ''
                
                if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'] or content_type.startswith('image/'):
                    return "image"
                elif ext in ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'] or content_type.startswith('audio/'):
                    return "audio"
                elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'] or content_type.startswith('video/'):
                    return "video"
                else:
                    return "document"
            
            file_type = determine_file_type(filename, content_type)
            
            file_data = {
                "id": file_id,
                "user_id": user_id,
                "message_id": message_id,
                "dify_file_id": dify_file_id,
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type,
                "content_type": content_type,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.from_("dify_files").insert(file_data).execute()
            
            if not result.data:
                raise Exception("文件信息保存失败")
            
            created_data = result.data[0]
            logger.info(f"成功保存文件信息: {filename} -> {dify_file_id}")
            
            return DifyFile(
                id=created_data["id"],
                user_id=created_data["user_id"],
                message_id=created_data.get("message_id"),
                dify_file_id=created_data["dify_file_id"],
                filename=created_data["filename"],
                file_size=created_data["file_size"],
                file_type=created_data["file_type"],
                content_type=created_data["content_type"],
                created_at=datetime.fromisoformat(created_data["created_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"保存文件信息失败: {e}")
            raise Exception(f"保存文件信息失败: {str(e)}")
    
    async def get_file_info(self, dify_file_id: str) -> Optional[DifyFile]:
        """
        根据Dify文件ID获取文件信息
        
        Args:
            dify_file_id: Dify文件ID
            
        Returns:
            文件对象或None
        """
        try:
            result = self.supabase.from_("dify_files").select("*").eq(
                "dify_file_id", dify_file_id
            ).execute()
            
            if not result.data:
                return None
            
            data = result.data[0]
            return DifyFile(
                id=data["id"],
                user_id=data["user_id"],
                message_id=data.get("message_id"),
                dify_file_id=data["dify_file_id"],
                filename=data["filename"],
                file_size=data["file_size"],
                file_type=data["file_type"],
                content_type=data["content_type"],
                created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    async def get_user_files(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[DifyFile]:
        """
        获取用户的文件列表
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            文件列表
        """
        try:
            result = self.supabase.from_("dify_files").select("*").eq(
                "user_id", user_id
            ).order(
                "created_at", desc=True
            ).range(
                offset, offset + limit - 1
            ).execute()
            
            files = []
            for data in result.data:
                files.append(DifyFile(
                    id=data["id"],
                    user_id=data["user_id"],
                    message_id=data.get("message_id"),
                    dify_file_id=data["dify_file_id"],
                    filename=data["filename"],
                    file_size=data["file_size"],
                    file_type=data["file_type"],
                    content_type=data["content_type"],
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
                ))
            
            logger.info(f"获取用户 {user_id} 的 {len(files)} 个文件")
            return files
            
        except Exception as e:
            logger.error(f"获取用户文件列表失败: {e}")
            return []
    
    async def record_point_transaction(
        self,
        user_id: str,
        conversation_id: str,
        transaction_type: str,
        points_amount: int,
        model_used: str,
        reason: str,
        message_id: Optional[str] = None,
        usage_data: Optional[Dict[str, Any]] = None
    ) -> DifyPointTransaction:
        """
        记录积分交易
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            transaction_type: 交易类型 (deduct, refund, adjustment)
            points_amount: 积分数量
            model_used: 使用的模型
            reason: 交易原因
            message_id: 关联的消息ID
            usage_data: 使用统计数据
            
        Returns:
            积分交易记录
        """
        try:
            transaction_id = str(uuid.uuid4())
            
            transaction_data = {
                "id": transaction_id,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "message_id": message_id,
                "transaction_type": transaction_type,
                "points_amount": points_amount,
                "model_used": model_used,
                "usage_data": json.dumps(usage_data) if usage_data else None,
                "reason": reason,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.from_("dify_point_transactions").insert(transaction_data).execute()
            
            if not result.data:
                raise Exception("积分交易记录保存失败")
            
            created_data = result.data[0]
            logger.info(f"成功记录积分交易: {transaction_type} {points_amount} 积分 (模型: {model_used})")
            
            return DifyPointTransaction(
                id=created_data["id"],
                user_id=created_data["user_id"],
                conversation_id=created_data["conversation_id"],
                message_id=created_data.get("message_id"),
                transaction_type=created_data["transaction_type"],
                points_amount=created_data["points_amount"],
                model_used=created_data["model_used"],
                usage_data=json.loads(created_data["usage_data"]) if created_data.get("usage_data") else None,
                reason=created_data["reason"],
                created_at=datetime.fromisoformat(created_data["created_at"].replace('Z', '+00:00'))
            )
            
        except Exception as e:
            logger.error(f"记录积分交易失败: {e}")
            raise Exception(f"记录积分交易失败: {str(e)}")
    
    async def get_user_point_transactions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[DifyPointTransaction]:
        """
        获取用户的积分交易记录
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            积分交易记录列表
        """
        try:
            result = self.supabase.from_("dify_point_transactions").select("*").eq(
                "user_id", user_id
            ).order(
                "created_at", desc=True
            ).range(
                offset, offset + limit - 1
            ).execute()
            
            transactions = []
            for data in result.data:
                transactions.append(DifyPointTransaction(
                    id=data["id"],
                    user_id=data["user_id"],
                    conversation_id=data["conversation_id"],
                    message_id=data.get("message_id"),
                    transaction_type=data["transaction_type"],
                    points_amount=data["points_amount"],
                    model_used=data["model_used"],
                    usage_data=json.loads(data["usage_data"]) if data.get("usage_data") else None,
                    reason=data["reason"],
                    created_at=datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
                ))
            
            logger.info(f"获取用户 {user_id} 的 {len(transactions)} 条积分交易记录")
            return transactions
            
        except Exception as e:
            logger.error(f"获取积分交易记录失败: {e}")
            return [] 