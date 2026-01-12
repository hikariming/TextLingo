"""
Dify API 端点 - 提供与 Dify chatflow 的集成接口
支持流式对话、会话管理和用户积分扣除
"""

import json
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.services.dify_service import dify_service
from app.schemas import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Dify 聊天请求模型"""
    query: str = Field(..., description="用户输入的问题", min_length=1, max_length=2000)
    conversation_id: Optional[str] = Field(None, description="会话ID（可选）")
    inputs: Optional[dict] = Field(default_factory=dict, description="额外输入参数")
    flow_id: Optional[str] = Field(None, description="指定使用的工作流ID（可选，默认使用主要工作流）")


class ConversationListRequest(BaseModel):
    """获取会话列表请求模型"""
    limit: int = Field(default=20, description="会话数量限制", ge=1, le=100)


class MessageListRequest(BaseModel):
    """获取消息列表请求模型"""
    conversation_id: str = Field(..., description="会话ID")
    limit: int = Field(default=20, description="消息数量限制", ge=1, le=100)


class WorkflowRequest(BaseModel):
    """Dify 工作流请求模型"""
    flow_id: str = Field(..., description="工作流ID")
    inputs: Optional[dict] = Field(default_factory=dict, description="工作流输入参数")


class WorkflowJsonRequest(BaseModel):
    """Dify 工作流 JSON 请求模型（用于已上传文件）"""
    flow_id: str = Field(..., description="工作流ID")
    inputs: dict = Field(default_factory=dict, description="工作流输入参数")
    response_mode: str = Field("blocking", description="响应模式")


@router.post("/chat", summary="与 Dify chatflow 进行流式对话")
async def chat_with_dify(
    request: ChatRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    与 Dify chatflow 进行流式对话
    
    - **query**: 用户输入的问题（必填）
    - **conversation_id**: 会话ID（可选，用于续接之前的对话）
    - **inputs**: 额外输入参数（可选）
    - **flow_id**: 指定使用的工作流ID（可选）
    
    返回: 流式响应数据（SSE格式）
    消耗积分: 根据指定工作流的配置
    """
    try:
        user_id = current_user.id
        
        # 根据flow_id创建对应的服务实例
        from app.services.dify_service import DifyService
        if request.flow_id:
            current_dify_service = DifyService(flow_id=request.flow_id)
        else:
            current_dify_service = dify_service  # 使用默认全局实例
        
        # 创建流式响应生成器
        async def stream_generator():
            try:
                async for chunk in current_dify_service.chat_with_flow(
                    user_id=user_id,
                    query=request.query,
                    conversation_id=request.conversation_id,
                    inputs=request.inputs
                ):
                    # 转换为 SSE 格式
                    yield f"data: {chunk}\n\n"
                    
                # 发送结束标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Dify 流式对话错误: {e}", exc_info=True)
                import json
                error_data = {
                    "event": "error",
                    "data": {"message": str(e)}
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用 Nginx 缓冲
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dify 聊天接口错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dify 聊天服务错误: {str(e)}"
        )


@router.get("/conversations", summary="获取用户的会话列表")
async def get_conversations(
    limit: int = 20,
    flow_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    获取当前用户的 Dify 会话列表
    
    - **limit**: 返回的会话数量限制（默认20，最大100）
    - **flow_id**: 指定工作流ID（可选，默认使用主要工作流）
    
    返回: 会话列表数据
    """
    try:
        user_id = current_user.id
        
        # 根据flow_id创建对应的服务实例
        from app.services.dify_service import DifyService
        if flow_id:
            current_dify_service = DifyService(flow_id=flow_id)
        else:
            current_dify_service = dify_service  # 使用默认全局实例
        
        conversations = await current_dify_service.get_user_conversations(
            user_id=user_id,
            limit=min(limit, 100)  # 限制最大值
        )
        
        return {
            "success": True,
            "data": conversations
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Dify 会话列表错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话列表失败: {str(e)}"
        )


@router.get("/conversations/{conversation_id}/messages", summary="获取会话的消息历史")
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 20,
    flow_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    获取指定会话的消息历史
    
    - **conversation_id**: 会话ID
    - **limit**: 返回的消息数量限制（默认20，最大100）
    - **flow_id**: 指定工作流ID（可选，默认使用主要工作流）
    
    返回: 消息历史数据
    """
    try:
        user_id = current_user.id
        
        # 根据flow_id创建对应的服务实例
        from app.services.dify_service import DifyService
        if flow_id:
            current_dify_service = DifyService(flow_id=flow_id)
        else:
            current_dify_service = dify_service  # 使用默认全局实例
        
        messages = await current_dify_service.get_conversation_messages(
            user_id=user_id,
            conversation_id=conversation_id,
            limit=min(limit, 100)  # 限制最大值
        )
        
        return {
            "success": True,
            "data": messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 Dify 会话消息错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取会话消息失败: {str(e)}"
        )


@router.get("/config", summary="获取 Dify 配置信息")
async def get_dify_config(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    获取 Dify 相关配置信息（不包含敏感信息）
    
    返回: 配置信息和可用的工作流列表
    """
    try:
        from app.core.dify_config import dify_config
        
        # 获取所有活跃的工作流
        active_flows = dify_config.get_all_active_flows()
        
        # 获取默认工作流
        default_flow = None
        if active_flows:
            default_flow = active_flows[0]  # 第一个作为默认
        
        flows_info = []
        for flow in active_flows:
            flows_info.append({
                "id": flow.id,
                "name": flow.name,
                "flow_type": flow.flow_type,
                "points_cost": flow.points_cost,
                "description": flow.description,
                "use_cases": flow.use_cases
            })
        
        return {
            "success": True,
            "data": {
                "available": len(active_flows) > 0,
                "default_points_cost": default_flow.points_cost if default_flow else 30,
                "flows": flows_info,
                "total_flows": len(active_flows)
            }
        }
        
    except Exception as e:
        logger.error(f"获取 Dify 配置错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )


@router.post("/workflow/run", summary="运行 Dify 工作流（阻塞模式）")
async def run_workflow(
    request: Request,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    运行 Dify 工作流并等待最终结果
    
    支持 multipart/form-data 格式：
    - **flow_id**: 工作流ID（必填）
    - **inputs**: 工作流输入参数（JSON字符串，可选）
    - **file** 或其他文件字段: 根据工作流 input_schema 定义的文件参数
    
    返回: Dify工作流执行完毕后的完整JSON结果
    """
    try:
        user_id = current_user.id
        
        # 解析 multipart/form-data
        form = await request.form()
        
        # 获取基本参数
        flow_id = form.get("flow_id")
        if not flow_id:
            raise HTTPException(status_code=400, detail="缺少必要参数: flow_id")
        
        # 解析 inputs 参数
        inputs_str = form.get("inputs", "{}")
        try:
            parsed_inputs = json.loads(inputs_str) if inputs_str else {}
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="inputs 参数必须是有效的JSON格式")
        
        # 创建工作流服务实例
        from app.services.dify_service import DifyService
        try:
            workflow_service = DifyService(flow_id=flow_id)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"工作流 {flow_id} 不存在或未启用")
            raise
        
        # 动态处理文件参数 - 根据工作流的 input_schema
        files_data = {}
        if workflow_service.flow_config and workflow_service.flow_config.input_schema:
            for param in workflow_service.flow_config.input_schema:
                if param.type == 'file':
                    # 查找对应的文件字段
                    file_field = form.get(param.name)
                    if file_field and hasattr(file_field, 'read'):
                        # 这是一个上传的文件
                        file_content = await file_field.read()
                        files_data[param.name] = {
                            'content': file_content, 
                            'filename': file_field.filename or 'unknown',
                            'content_type': file_field.content_type or 'application/octet-stream'
                        }
                        logger.info(f"接收到文件参数 '{param.name}': {file_field.filename}, 大小: {len(file_content)} bytes")
                    elif param.required:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"工作流 '{flow_id}' 需要一个名为 '{param.name}' 的文件参数，但未提供"
                        )
        
        # 兜底处理：如果没有找到任何文件但表单中有 'file' 字段
        if not files_data:
            file_field = form.get("file")
            if file_field and hasattr(file_field, 'read'):
                file_content = await file_field.read()
                files_data['file'] = {
                    'content': file_content,
                    'filename': file_field.filename or 'unknown',
                    'content_type': file_field.content_type or 'application/octet-stream'
                }
                logger.info(f"使用默认文件字段 'file': {file_field.filename}, 大小: {len(file_content)} bytes")
        
        logger.info(f"工作流 {flow_id} 调用 - 用户: {user_id}, inputs: {parsed_inputs}, files: {list(files_data.keys())}")
        
        # 调用工作流
        result = await workflow_service.run_workflow(
            user_id=user_id,
            inputs=parsed_inputs,
            files=files_data if files_data else None
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dify 工作流接口错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dify 工作流服务错误: {str(e)}")


@router.post("/workflow/run-json", summary="运行 Dify 工作流（JSON模式，用于已上传文件）")
async def run_workflow_json(
    request: WorkflowJsonRequest,
    stream: bool = False,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    运行 Dify 工作流（JSON模式，用于已上传文件ID）
    
    支持 JSON 格式请求，适用于已经上传到 Dify 的文件：
    - **flow_id**: 工作流ID（必填）
    - **inputs**: 工作流输入参数，包含文件引用格式
    - **response_mode**: 响应模式（blocking/streaming）
    
    文件引用格式：
    ```json
    {
        "file": {
            "type": "image",
            "transfer_method": "local_file",
            "url": "",
            "upload_file_id": "file-id-here"
        }
    }
    ```
    
    返回: Dify工作流执行结果
    """
    try:
        user_id = current_user.id
        
        # 创建工作流服务实例
        from app.services.dify_service import DifyService
        try:
            workflow_service = DifyService(flow_id=request.flow_id)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"工作流 {request.flow_id} 不存在或未启用")
            raise
        
        logger.info(f"JSON模式工作流 {request.flow_id} 调用 - 用户: {user_id}, inputs: {request.inputs}, stream: {stream}")
        
        if stream:
            # 流式模式
            async def stream_generator():
                try:
                    async for chunk in workflow_service.run_workflow_with_json_stream(
                        user_id=user_id,
                        inputs=request.inputs
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"JSON工作流流式模式错误: {e}", exc_info=True)
                    import json
                    error_data = {
                        "event": "error",
                        "data": {"message": str(e)}
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        else:
            # 阻塞模式
            result = await workflow_service.run_workflow_with_json(
                user_id=user_id,
                inputs=request.inputs,
                response_mode=request.response_mode
            )
            return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dify 工作流JSON接口错误: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dify 工作流服务错误: {str(e)}")


@router.post("/files/upload", summary="上传文件到 Dify")
async def upload_file_to_dify(
    file: UploadFile = File(...),
    file_type: str = Form("document"),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    将文件上传到 Dify 并返回文件ID
    
    - **file**: 要上传的文件
    - **file_type**: 文件类型 (image/audio/video/document)
    
    返回: 包含 upload_file_id 和 file_type 的响应
    """
    try:
        user_id = current_user.id
        
        # 读取文件内容
        file_content = await file.read()
        
        # 使用默认的 Dify 服务实例
        file_info = {
            'content': file_content,
            'filename': file.filename or 'unknown',
            'content_type': file.content_type or 'application/octet-stream'
        }
        
        # 上传文件到 Dify
        upload_file_id = await dify_service._upload_dify_file(user_id, file_info)
        
        # 根据文件类型确定返回类型
        def get_file_type_from_filename(filename: str, content_type: str) -> str:
            if not filename:
                return file_type
                
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'] or (content_type and content_type.startswith('image/')):
                return "image"
            elif ext in ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'] or (content_type and content_type.startswith('audio/')):
                return "audio"
            elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'] or (content_type and content_type.startswith('video/')):
                return "video"
            else:
                return "document"
        
        detected_type = get_file_type_from_filename(file.filename or '', file.content_type or '')
        
        return {
            "upload_file_id": upload_file_id,
            "file_type": detected_type,
            "filename": file.filename,
            "size": len(file_content)
        }
        
    except Exception as e:
        logger.error(f"文件上传到 Dify 失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")