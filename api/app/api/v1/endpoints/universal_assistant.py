"""
通用助手API端点 - 支持多模型选择的Dify聊天功能
"""

import json
import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user_with_token
from app.services.dify_universal_service import DifyUniversalService
from app.services.dify_conversation_service import DifyConversationService
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 请求模型
class ChatRequest(BaseModel):
    query: str = Field(..., description="用户输入的问题")
    model: str = Field(default="glm45", description="选择的模型ID")
    conversation_id: Optional[str] = Field(None, description="会话ID，为空则创建新会话")
    files: Optional[List[str]] = Field(None, description="已上传的文件ID列表")

class ChatWithFilesRequest(BaseModel):
    query: str = Field(..., description="用户输入的问题")
    model: str = Field(default="glm45", description="选择的模型ID")
    conversation_id: Optional[str] = Field(None, description="会话ID，为空则创建新会话")

# 响应模型
class ConversationResponse(BaseModel):
    id: str
    title: str
    model: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    points_consumed: int
    created_at: str

@router.post("/chat", summary="发送聊天消息")
async def chat_with_universal_assistant(
    request: ChatRequest,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    与通用助手聊天
    
    支持多模型选择、会话管理和流式响应
    """
    current_user, access_token = user_info
    
    try:
        # 初始化服务
        dify_service = DifyUniversalService()
        conversation_service = DifyConversationService()
        
        # 验证模型权限
        await dify_service.validate_model_access(current_user.id, request.model)
        
        # 处理会话
        if request.conversation_id:
            # 验证会话是否属于用户
            conversation = await conversation_service.get_conversation(
                current_user.id, request.conversation_id, access_token
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
        else:
            # 创建新会话
            conversation = await conversation_service.create_conversation(
                user_id=current_user.id,
                model=request.model,
                access_token=access_token,
                flow_id="universal-assistant"
            )
            request.conversation_id = conversation.id
        
        # 保存用户消息
        user_message = await conversation_service.save_message(
            conversation_id=request.conversation_id,
            user_id=current_user.id,
            role="user",
            content=request.query,
            access_token=access_token
        )
        
        # 准备文件参数
        files_param = []
        if request.files:
            for file_id in request.files:
                file_info = await conversation_service.get_file_info(file_id)
                if file_info:
                    files_param.append({
                        "type": file_info.file_type,
                        "transfer_method": "local_file",
                        "url": "",
                        "upload_file_id": file_id
                    })
        
        # 预扣积分并获取信息
        try:
            points_deducted, points_before, pre_deducted_points = await dify_service.deduct_points_for_model(current_user.id, request.model)
        except HTTPException as e:
            # 如果积分不足，直接抛出异常
            raise e
        except Exception as e:
            logger.error(f"预扣积分失败: {e}")
            points_deducted, points_before, pre_deducted_points = False, 0, 0
        
        # 流式响应生成器
        async def response_generator():
            dify_conversation_id_from_stream = None
            our_conversation_id = request.conversation_id
            assistant_message_id = None
            full_response = ""
            
            try:
                # 调用chat_stream时不再进行积分预扣（已在上面处理）
                async for chunk in dify_service.chat_stream(
                    user_id=current_user.id,
                    query=request.query,
                    model=request.model,
                    conversation_id=request.conversation_id,
                    files=files_param,
                    skip_points_deduction=True  # 跳过积分预扣
                ):
                    chunk_data = json.loads(chunk)
                    
                    # 提取并保存Dify的conversation_id
                    dify_id_in_chunk = chunk_data.get("conversation_id")
                    if dify_id_in_chunk and not dify_conversation_id_from_stream:
                        dify_conversation_id_from_stream = dify_id_in_chunk
                        # 更新本地会话的Dify ID
                        if our_conversation_id:
                            await conversation_service.update_conversation_dify_id(
                                our_conversation_id, dify_conversation_id_from_stream
                            )

                    # 在将数据发送到前端前，始终将会话ID替换为我们自己的ID
                    chunk_data["conversation_id"] = our_conversation_id
                    
                    # 处理消息事件
                    if chunk_data.get("event") == "message":
                        if not assistant_message_id:
                            assistant_message_id = chunk_data.get("message_id")
                        
                        answer = chunk_data.get("answer", "")
                        full_response += answer
                        
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    # 处理消息结束事件
                    elif chunk_data.get("event") == "message_end":
                        assistant_message_id = chunk_data.get("message_id") or assistant_message_id
                        
                        # 提取使用统计
                        metadata = chunk_data.get("metadata", {})
                        usage = metadata.get("usage", {})
                        final_usage_data = usage
                        
                        # 保存助手回复
                        if assistant_message_id and full_response:
                            # 从usage数据中提取token信息
                            input_tokens = int(usage.get("prompt_tokens", 0))
                            output_tokens = int(usage.get("completion_tokens", 0))
                            total_tokens = int(usage.get("total_tokens", 0))
                            
                            # 计算实际消耗的积分
                            actual_points = dify_service.calculate_model_points(request.model, usage)
                            
                            # 调整积分差额（预扣 vs 实际消费）
                            if points_deducted and pre_deducted_points > 0:
                                try:
                                    await dify_service.adjust_final_points(current_user.id, pre_deducted_points, actual_points)
                                    logger.info(f"用户 {current_user.id} 积分调整: 预扣{pre_deducted_points} -> 实际{actual_points}")
                                except Exception as adjust_error:
                                    logger.error(f"积分调整失败: {adjust_error}")
                            
                            assistant_message = await conversation_service.save_message(
                                conversation_id=our_conversation_id,
                                user_id=current_user.id,
                                role="assistant",
                                content=full_response,
                                access_token=access_token,
                                dify_message_id=assistant_message_id,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                total_tokens=total_tokens,
                                points_consumed=actual_points,
                                metadata={"usage": usage}
                            )
                            
                            # 记录积分交易
                            if usage:
                                try:
                                    actual_points = dify_service.calculate_model_points(request.model, usage)
                                    await conversation_service.record_point_transaction(
                                        user_id=current_user.id,
                                        conversation_id=our_conversation_id,
                                        transaction_type="deduct",
                                        points_amount=actual_points,
                                        model_used=request.model,
                                        reason=f"使用模型 {request.model} 进行对话",
                                        message_id=assistant_message.id,
                                        usage_data=usage
                                    )
                                except Exception as transaction_error:
                                    logger.error(f"记录积分交易失败: {transaction_error}")
                        
                        # 更新会话
                        await conversation_service.update_conversation_activity(
                            our_conversation_id, access_token
                        )
                        
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                    
                    # 其他事件直接转发
                    else:
                        yield f"data: {json.dumps(chunk_data)}\n\n"
                        
            except Exception as e:
                logger.error(f"流式响应错误: {e}")
                
                # 如果出现异常且有预扣积分，需要全额退费（不收保底费用）
                if points_deducted and points_before > 0:
                    try:
                        await dify_service.refund_points(current_user.id, points_before, f"API调用异常: {str(e)}")
                        logger.info(f"用户 {current_user.id} 因异常全额退费成功，不收保底费用")
                    except Exception as refund_error:
                        logger.error(f"异常退费失败: {refund_error}")
                
                error_response = {
                    "event": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_response)}\n\n"
        
        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error(f"聊天请求失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天请求失败: {str(e)}")

@router.post("/chat-with-files", summary="发送聊天消息（带文件上传）")
async def chat_with_files(
    query: str = Form(...),
    model: str = Form(default="glm45"),
    conversation_id: Optional[str] = Form(None),
    files: List[UploadFile] = File(...),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    带文件上传的聊天功能
    """
    current_user, access_token = user_info
    
    try:
        # 初始化服务
        dify_service = DifyUniversalService()
        conversation_service = DifyConversationService()
        
        # 验证模型权限
        await dify_service.validate_model_access(current_user.id, model)
        
        # 上传文件到Dify
        uploaded_files = []
        for file in files:
            try:
                # 读取文件内容
                file_content = await file.read()
                
                # 上传到Dify
                dify_file_id = await dify_service.upload_file(
                    user_id=current_user.id,
                    file_content=file_content,
                    filename=file.filename,
                    content_type=file.content_type
                )
                
                # 保存文件信息
                file_info = await conversation_service.save_file(
                    user_id=current_user.id,
                    dify_file_id=dify_file_id,
                    filename=file.filename,
                    file_size=len(file_content),
                    content_type=file.content_type
                )
                
                uploaded_files.append({
                    "type": file_info.file_type,
                    "transfer_method": "local_file", 
                    "url": "",
                    "upload_file_id": dify_file_id
                })
                
            except Exception as e:
                logger.error(f"文件上传失败 {file.filename}: {e}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"文件上传失败 {file.filename}: {str(e)}"
                )
        
        # 处理会话
        if conversation_id:
            conversation = await conversation_service.get_conversation(
                current_user.id, conversation_id
            )
            if not conversation:
                raise HTTPException(status_code=404, detail="会话不存在")
        else:
            conversation = await conversation_service.create_conversation(
                user_id=current_user.id,
                model=model,
                flow_id="universal-assistant"
            )
            conversation_id = conversation.id
        
        # 保存用户消息
        user_message = await conversation_service.save_message(
            conversation_id=conversation_id,
            user_id=current_user.id,
            role="user",
            content=query,
            model=model,
            files=[f["upload_file_id"] for f in uploaded_files]
        )
        
        # 流式响应生成器
        async def response_generator():
            assistant_message_id = None
            full_response = ""
            
            try:
                async for chunk in dify_service.chat_stream(
                    user_id=current_user.id,
                    query=query,
                    model=model,
                    conversation_id=conversation_id,
                    files=uploaded_files
                ):
                    chunk_data = json.loads(chunk)
                    
                    if chunk_data.get("event") == "message":
                        if not assistant_message_id:
                            assistant_message_id = chunk_data.get("message_id")
                        
                        answer = chunk_data.get("answer", "")
                        full_response += answer
                        
                        yield f"data: {chunk}\n\n"
                    
                    elif chunk_data.get("event") == "message_end":
                        assistant_message_id = chunk_data.get("message_id") or assistant_message_id
                        
                        metadata = chunk_data.get("metadata", {})
                        usage = metadata.get("usage", {})
                        
                        if assistant_message_id and full_response:
                            await conversation_service.save_message(
                                conversation_id=conversation_id,
                                user_id=current_user.id,
                                role="assistant",
                                content=full_response,
                                model=model,
                                dify_message_id=assistant_message_id,
                                usage_data=usage
                            )
                        
                        await conversation_service.update_conversation_activity(
                            conversation_id
                        )
                        
                        yield f"data: {chunk}\n\n"
                    
                    else:
                        yield f"data: {chunk}\n\n"
                        
            except Exception as e:
                logger.error(f"文件聊天流式响应错误: {e}")
                error_response = {
                    "event": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_response)}\n\n"
        
        return StreamingResponse(
            response_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
        
    except Exception as e:
        logger.error(f"文件聊天请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件聊天请求失败: {str(e)}")

@router.get("/conversations", summary="获取用户的会话列表")
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户的会话列表"""
    current_user, access_token = user_info
    
    try:
        conversation_service = DifyConversationService()
        conversations = await conversation_service.get_user_conversations(
            user_id=current_user.id,
            access_token=access_token,
            limit=limit,
            offset=offset
        )
        
        return {
            "conversations": [
                ConversationResponse(
                    id=conv.id,
                    title=conv.title,
                    model=conv.model_config.get("selected_model", "unknown"),
                    created_at=conv.created_at.isoformat(),
                    updated_at=conv.updated_at.isoformat()
                ) for conv in conversations
            ]
        }
        
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")

@router.get("/conversations/{conversation_id}/messages", summary="获取会话消息")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 20,
    offset: int = 0,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取会话的消息历史"""
    current_user, access_token = user_info
    
    try:
        conversation_service = DifyConversationService()
        
        # 验证会话权限
        conversation = await conversation_service.get_conversation(
            current_user.id, conversation_id, access_token
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        messages = await conversation_service.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "messages": [
                MessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    role=msg.role,
                    content=msg.content,
                    input_tokens=msg.input_tokens,
                    output_tokens=msg.output_tokens,
                    total_tokens=msg.total_tokens,
                    points_consumed=msg.points_consumed,
                    created_at=msg.created_at.isoformat()
                ) for msg in messages
            ]
        }
        
    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取会话消息失败: {str(e)}")

@router.delete("/conversations/{conversation_id}", summary="删除会话")
async def delete_conversation(
    conversation_id: str,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """删除会话"""
    current_user, access_token = user_info
    
    try:
        conversation_service = DifyConversationService()
        
        # 验证会话权限
        conversation = await conversation_service.get_conversation(
            current_user.id, conversation_id, access_token
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        await conversation_service.delete_conversation(conversation_id)
        
        return {"result": "success"}
        
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")

@router.get("/models", summary="获取可用模型列表")
async def get_available_models(
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户可用的模型列表"""
    current_user, access_token = user_info
    
    try:
        dify_service = DifyUniversalService()
        models = await dify_service.get_available_models(current_user.id)
        
        return {"models": models}
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")

@router.post("/upload-file", summary="上传文件到Dify")
async def upload_file_to_dify(
    file: UploadFile = File(...),
    user_info: tuple = Depends(get_current_user_with_token)
):
    """
    上传文件到Dify并返回文件ID
    """
    current_user, access_token = user_info
    
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 上传到Dify
        dify_service = DifyUniversalService()
        dify_file_id = await dify_service.upload_file(
            user_id=current_user.id,
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # 保存文件信息
        conversation_service = DifyConversationService()
        file_info = await conversation_service.save_file(
            user_id=current_user.id,
            dify_file_id=dify_file_id,
            filename=file.filename,
            file_size=len(file_content),
            content_type=file.content_type
        )
        
        return {
            "file_id": dify_file_id,
            "filename": file.filename,
            "file_size": len(file_content),
            "file_type": file_info.file_type,
            "content_type": file.content_type
        }
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")

@router.get("/files", summary="获取用户文件列表")
async def get_user_files(
    limit: int = 20,
    offset: int = 0,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户的文件列表"""
    current_user, access_token = user_info
    
    try:
        conversation_service = DifyConversationService()
        files = await conversation_service.get_user_files(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return {
            "files": [
                {
                    "id": f.id,
                    "dify_file_id": f.dify_file_id,
                    "filename": f.filename,
                    "file_size": f.file_size,
                    "file_type": f.file_type,
                    "content_type": f.content_type,
                    "created_at": f.created_at.isoformat()
                } for f in files
            ]
        }
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@router.get("/point-transactions", summary="获取积分交易记录")
async def get_point_transactions(
    limit: int = 20,
    offset: int = 0,
    user_info: tuple = Depends(get_current_user_with_token)
):
    """获取用户的积分交易记录"""
    current_user, access_token = user_info
    
    try:
        conversation_service = DifyConversationService()
        transactions = await conversation_service.get_user_point_transactions(
            user_id=current_user.id,
            limit=limit,
            offset=offset
        )
        
        return {
            "transactions": [
                {
                    "id": t.id,
                    "conversation_id": t.conversation_id,
                    "message_id": t.message_id,
                    "transaction_type": t.transaction_type,
                    "points_amount": t.points_amount,
                    "model_used": t.model_used,
                    "reason": t.reason,
                    "usage_data": t.usage_data,
                    "created_at": t.created_at.isoformat()
                } for t in transactions
            ]
        }
        
    except Exception as e:
        logger.error(f"获取积分交易记录失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取积分交易记录失败: {str(e)}") 