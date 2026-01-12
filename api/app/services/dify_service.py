"""
Dify 服务层 - 处理与 Dify API 的集成
提供 chatflow 流式对话功能和用户积分管理
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Any, Optional
import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging_config import LoggingConfig
from app.core.dify_config import dify_config, get_default_flow, FlowType
from app.services.points_service import PointsService
from app.services.supabase_client import supabase_service
from app.services.user_service import UserService # 导入 UserService

logger = LoggingConfig.get_logger_for_service("dify_service")


class DifyService:
    """Dify API 集成服务"""
    
    def __init__(self, flow_id: Optional[str] = None):
        """初始化 Dify 服务
        
        Args:
            flow_id: 指定使用的工作流ID，如果为None则使用默认的chatflow
        """
        # 获取工作流配置
        if flow_id:
            self.flow_config = dify_config.get_flow(flow_id)
            if not self.flow_config:
                raise HTTPException(
                    status_code=404,
                    detail=f"未找到工作流配置: {flow_id}"
                )
        else:
            # 使用默认的chatflow
            self.flow_config = get_default_flow(FlowType.CHATFLOW)
            if not self.flow_config:
                # 兼容性处理：如果没有配置，使用环境变量
                if settings.dify_legacy_api_url and settings.dify_legacy_api_token:
                    self.api_url = settings.dify_legacy_api_url
                    self.api_token = settings.dify_legacy_api_token
                    self.points_cost = 30  # 默认积分消耗
                    self.flow_config = None
                else:
                    raise HTTPException(
                        status_code=500,
                        detail="未配置任何Dify工作流，请检查dify_config.json或环境变量"
                    )
        
        # 如果有工作流配置，使用配置的值
        if self.flow_config:
            self.api_url = self.flow_config.api_url
            self.api_token = self.flow_config.api_token
            self.points_cost = self.flow_config.points_cost
            self.flow_id = self.flow_config.id
            self.flow_type = self.flow_config.flow_type
        else:
            self.flow_id = "legacy"
            self.flow_type = FlowType.CHATFLOW
            
        try:
            self.points_service = PointsService()
            if LoggingConfig.should_log_debug():
                logger.debug("积分服务初始化成功")
        except Exception as e:
            logger.error(f"初始化积分服务失败: {e}", exc_info=True)
            self.points_service = None
        
    def _validate_config(self) -> None:
        """验证 Dify 配置是否完整"""
        if not self.api_url or not self.api_token:
            if self.flow_config:
                raise HTTPException(
                    status_code=500,
                    detail=f"工作流 {self.flow_id} 配置不完整，请检查 dify_config.json 中的 api_url 和 api_token"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Dify 配置不完整，请检查 dify_config.json 或环境变量 DIFY_LEGACY_API_URL 和 DIFY_LEGACY_API_TOKEN"
                )
    
    async def chat_with_flow(
        self,
        user_id: str,
        query: str,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        与 Dify chatflow 进行流式对话
        
        Args:
            user_id: 用户ID
            query: 用户输入的问题
            conversation_id: 会话ID（可选）
            **kwargs: 额外参数
            
        Yields:
            流式响应数据
        """
        self._validate_config()
        
        # 检查并扣除积分 - 使用简单的固定积分扣除
        points_deducted = False
        points_before = 0
        
        if self.points_service:
            try:
                # 获取用户当前积分
                balance = await self.points_service.get_user_balance(user_id)
                if not balance:
                    logger.warning(f"无法获取用户 {user_id} 的积分余额，可能由于旧bug导致用户资料不存在。将为用户创建资料并本次免除积分。")
                    try:
                        # 尝试为用户创建资料
                        user_service = UserService() # 使用 service role
                        profile = await user_service.get_user_profile(user_id)
                        if profile:
                            if LoggingConfig.should_log_debug():
                                logger.debug(f"成功为用户 {user_id} 创建或确认了个人资料。")
                        else:
                            logger.error(f"为用户 {user_id} 自动创建资料失败。")
                    except Exception as e:
                        logger.error(f"为用户 {user_id} 自动创建资料时出现异常: {e}")

                    # 不抛出异常，继续执行
                
                elif balance.total_points < self.points_cost:
                    logger.warning(f"用户 {user_id} 积分不足: {balance.total_points} < {self.points_cost}")
                    raise HTTPException(
                        status_code=402,
                        detail=f"积分不足，当前积分: {balance.total_points}，需要 {self.points_cost} 积分"
                    )
                
                else:
                    points_before = balance.total_points
                    
                    # 使用绕过RLS的方法扣除积分
                    supabase = supabase_service.get_client()
                    new_points = points_before - self.points_cost
                    
                    # 方法1: 优先使用RPC函数更新积分（绕过RLS）
                    try:
                        rpc_result = supabase.rpc('update_user_points_bypass_rls', {
                            'p_user_id': user_id,
                            'p_new_points': new_points
                        }).execute()
                        
                        if rpc_result.data:
                            points_deducted = True
                            logger.info(f"RPC方法成功扣除 {self.points_cost} 积分，剩余积分: {new_points}")
                        else:
                            raise Exception("RPC更新积分失败")
                            
                    except Exception as rpc_error:
                        logger.warning(f"RPC方法更新积分失败: {rpc_error}，尝试直接更新")
                        
                        # 方法2: 回退到直接更新user_profiles表
                        update_result = supabase.from_("user_profiles").update({
                            "points": new_points
                        }).eq("user_id", user_id).execute()
                        
                        if not update_result.data:
                            raise HTTPException(
                                status_code=500,
                                detail="积分扣除失败"
                            )
                        
                        points_deducted = True
                        logger.info(f"直接更新成功扣除 {self.points_cost} 积分，剩余积分: {new_points}")
                    
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"积分扣除异常: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"积分扣除失败: {str(e)}"
                )
        else:
            # 积分服务不可用时的处理
            logger.warning("积分服务不可用，跳过积分检查")
            # 可以选择是否允许继续使用服务，这里选择允许但记录警告
            # 如果要严格控制，可以取消注释下面的代码
            # raise HTTPException(
            #     status_code=503,
            #     detail="积分服务暂时不可用，请稍后重试"
            # )
        
        # 准备请求数据
        payload = {
            "inputs": kwargs.get("inputs", {}),
            "query": query,
            "response_mode": "streaming",
            "user": user_id,
        }
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
            
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        try:
            if LoggingConfig.should_log_debug():
                logger.debug(f"发起 Dify 请求: {self.api_url}/chat-messages")
                logger.debug(f"请求数据: {payload}")
            
            # 发起流式请求
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.api_url}/chat-messages",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Dify API 错误: {response.status_code} - {error_text}")
                        
                        # API调用失败，退还积分
                        if points_deducted and self.points_service:
                            try:
                                supabase = supabase_service.get_client()
                                refund_points = points_before  # 恢复到原来的积分
                                supabase.from_("user_profiles").update({
                                    "points": refund_points
                                }).eq("user_id", user_id).execute()
                                if LoggingConfig.should_log_debug():
                                    logger.debug(f"Dify API调用失败，已退还 {self.points_cost} 积分")
                            except Exception as refund_error:
                                logger.error(f"积分退还失败: {refund_error}")
                        
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=f"Dify API 调用失败: {error_text.decode()}"
                        )
                    
                    # 积分已在API调用前扣除，这里不需要再次扣除
                    
                    # 流式处理响应
                    async for chunk in response.aiter_lines():
                        if chunk.strip():
                            try:
                                # 解析 SSE 格式数据
                                if chunk.startswith("data: "):
                                    data_str = chunk[6:]  # 移除 "data: " 前缀
                                    if data_str.strip() == "[DONE]":
                                        break
                                    
                                    data = json.loads(data_str)
                                    
                                    # 只返回有用的事件
                                    if data.get("event") in ["message", "agent_message", "message_end", "workflow_finished"]:
                                        yield json.dumps(data)
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"解析 Dify 响应数据失败: {e}, chunk: {chunk}")
                                continue
                                
        except httpx.TimeoutException as e:
            logger.error("Dify API 请求超时")
            # 超时也需要退还积分
            self._handle_simple_refund(points_deducted, user_id, points_before, "API请求超时")
            raise HTTPException(status_code=504, detail="Dify API 请求超时")
        except httpx.RequestError as e:
            logger.error(f"Dify API 请求错误: {e}")
            # 请求错误也需要退还积分
            self._handle_simple_refund(points_deducted, user_id, points_before, f"API请求错误: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Dify API 请求错误: {str(e)}")
        except HTTPException:
            # HTTPException 不处理退款，因为前面已经处理过了
            raise
        except Exception as e:
            logger.error(f"Dify 服务未知错误: {e}", exc_info=True)
            # 其他异常也需要退还积分
            self._handle_simple_refund(points_deducted, user_id, points_before, f"服务错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Dify 服务错误: {str(e)}")

    async def _upload_dify_file(self, user_id: str, file_info: Dict[str, Any]) -> Optional[str]:
        """
        上传文件到 Dify
        
        Args:
            user_id: 用户ID
            file_info: 文件信息字典，包含 'content', 'filename', 'content_type'
            
        Returns:
            上传成功后的文件ID，失败则返回 None 或抛出异常
        """
        upload_url = f"{self.api_url}/files/upload"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        
        # 根据文件扩展名和 content_type 确定文件类型
        def get_file_type(filename: str, content_type: str) -> str:
            """根据文件名和 content_type 确定 Dify 文件类型"""
            if not filename:
                return "TXT"  # 默认类型
                
            ext = filename.lower().split('.')[-1] if '.' in filename else ''
            
            # 文档类型
            if ext in ['txt', 'md', 'markdown']:
                return "TXT"
            elif ext in ['pdf']:
                return "PDF"
            elif ext in ['html', 'htm']:
                return "HTML"
            elif ext in ['xlsx', 'xls']:
                return "XLSX" if ext == 'xlsx' else "XLS"
            elif ext in ['docx']:
                return "DOCX"
            elif ext in ['csv']:
                return "CSV"
            elif ext in ['eml']:
                return "EML"
            elif ext in ['msg']:
                return "MSG"
            elif ext in ['pptx', 'ppt']:
                return "PPTX" if ext == 'pptx' else "PPT"
            elif ext in ['xml']:
                return "XML"
            elif ext in ['epub']:
                return "EPUB"
            # 图片类型
            elif ext in ['jpg', 'jpeg']:
                return "JPG"
            elif ext in ['png']:
                return "PNG"
            elif ext in ['gif']:
                return "GIF"
            elif ext in ['webp']:
                return "WEBP"
            elif ext in ['svg']:
                return "SVG"
            # 音频类型
            elif ext in ['mp3']:
                return "MP3"
            elif ext in ['m4a']:
                return "M4A"
            elif ext in ['wav']:
                return "WAV"
            elif ext in ['webm']:
                return "WEBM"
            elif ext in ['amr']:
                return "AMR"
            # 视频类型
            elif ext in ['mp4']:
                return "MP4"
            elif ext in ['mov']:
                return "MOV"
            elif ext in ['mpeg']:
                return "MPEG"
            elif ext in ['mpga']:
                return "MPGA"
            else:
                # 根据 content_type 进行二次判断
                if content_type:
                    if content_type.startswith('text/'):
                        return "TXT"
                    elif content_type == 'application/pdf':
                        return "PDF"
                    elif content_type.startswith('image/'):
                        return "JPG"  # 默认图片类型
                    elif content_type.startswith('audio/'):
                        return "MP3"  # 默认音频类型
                    elif content_type.startswith('video/'):
                        return "MP4"  # 默认视频类型
                
                return "TXT"  # 最终默认类型
        
        filename = file_info.get('filename', 'unknown')
        content_type = file_info.get('content_type', 'application/octet-stream')
        file_type = get_file_type(filename, content_type)
        
        files = {
            'file': (filename, file_info['content'], content_type)
        }
        data = {
            "user": user_id,
            "type": file_type  # 根据 Dify 官方文档添加文件类型
        }

        logger.info(f"准备上传文件到 Dify: {filename} (类型: {file_type}, 大小: {len(file_info['content'])} bytes)")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(upload_url, headers=headers, data=data, files=files)
            
            if response.status_code == 201:  # 201 Created
                response_data = response.json()
                file_id = response_data.get("id")
                logger.info(f"Dify 文件上传成功: id={file_id}, 文件: {filename}")
                return file_id
            else:
                logger.error(f"Dify 文件上传失败: {response.status_code} - {response.text}")
                # 根据Dify的错误格式抛出更详细的异常
                try:
                    error_data = response.json()
                    detail = f"Dify文件上传失败: {error_data.get('message', response.text)}"
                except json.JSONDecodeError:
                    detail = f"Dify文件上传失败: {response.status_code} - {response.text}"
                raise HTTPException(status_code=response.status_code, detail=detail)

        except httpx.RequestError as e:
            logger.error(f"Dify 文件上传请求错误: {e}")
            raise HTTPException(status_code=502, detail=f"Dify 文件上传请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"Dify 文件上传时发生未知错误: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Dify 文件上传时发生未知错误: {str(e)}")

    async def run_workflow(
        self,
        user_id: str,
        inputs: Dict[str, Any],
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        运行 Dify 工作流 (已根据官方文档重构为阻塞模式)
        """
        self._validate_config()
        
        if self.flow_type != FlowType.WORKFLOW:
            raise HTTPException(status_code=400, detail=f"流 {self.flow_id} 不是工作流类型")

        # 检查并扣除积分
        points_deducted, points_before = False, 0
        if self.points_service:
            try:
                balance = await self.points_service.get_user_balance(user_id)
                if balance and balance.total_points < self.points_cost:
                    raise HTTPException(status_code=402, detail=f"积分不足，需要 {self.points_cost}，当前: {balance.total_points}")
                
                if balance:
                    points_before = balance.total_points
                    supabase = supabase_service.get_client()
                    new_points = points_before - self.points_cost
                    
                    try:
                        rpc_result = supabase.rpc('update_user_points_bypass_rls', {
                            'p_user_id': user_id,
                            'p_new_points': new_points
                        }).execute()
                        
                        if rpc_result.data:
                            points_deducted = True
                            logger.info(f"工作流调用扣除 {self.points_cost} 积分")
                        else:
                            raise Exception("RPC更新积分失败")
                    except Exception as rpc_error:
                        logger.warning(f"RPC方法更新积分失败: {rpc_error}，尝试直接更新")
                        update_result = supabase.from_("user_profiles").update({
                            "points": new_points
                        }).eq("user_id", user_id).execute()
                        
                        if not update_result.data:
                            raise HTTPException(status_code=500, detail="积分扣除失败")
                        
                        points_deducted = True
                        logger.info(f"工作流调用直接更新成功扣除 {self.points_cost} 积分")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"积分扣除异常: {e}")
                raise HTTPException(status_code=500, detail=f"积分扣除失败: {str(e)}")

        # --- 根据 input_schema 构建最终输入 ---
        final_inputs = {}
        schema_files = {}
        
        # 1. 遍历 schema 定义
        for param in self.flow_config.input_schema:
            param_name = param.name
            
            # 2. 如果是文件类型
            if param.type == 'file':
                if files and param_name in files:
                    schema_files[param_name] = files[param_name]
                elif param.required:
                    raise HTTPException(status_code=400, detail=f"工作流 '{self.flow_id}' 需要一个名为 '{param_name}' 的文件输入，但未提供。")
            
            # 3. 如果是字符串等其他类型
            else:
                if param_name in inputs:
                    final_inputs[param_name] = inputs[param_name]
                elif param.required:
                    raise HTTPException(status_code=400, detail=f"工作流 '{self.flow_id}' 需要一个名为 '{param_name}' 的输入参数，但未提供。")
        
        # --- 处理文件上传（如果 schema 中有定义） ---
        if schema_files:
            try:
                # 假设我们一次只处理一个文件上传变量
                # TODO: 未来可扩展为支持多个文件变量
                file_variable_name, file_info = next(iter(schema_files.items()))
                
                upload_file_id = await self._upload_dify_file(user_id, file_info)
                
                # 根据文件类型确定 Dify 文件类型
                def get_dify_file_type(filename: str, content_type: str) -> str:
                    """根据文件名和 content_type 确定 Dify 文件类型"""
                    if not filename:
                        return "document"
                        
                    ext = filename.lower().split('.')[-1] if '.' in filename else ''
                    
                    # 图片类型
                    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'] or (content_type and content_type.startswith('image/')):
                        return "image"
                    # 音频类型  
                    elif ext in ['mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'] or (content_type and content_type.startswith('audio/')):
                        return "audio"
                    # 视频类型
                    elif ext in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'] or (content_type and content_type.startswith('video/')):
                        return "video"
                    # 默认为文档类型
                    else:
                        return "document"
                
                filename = file_info.get('filename', 'unknown')
                content_type = file_info.get('content_type', 'application/octet-stream')
                dify_file_type = get_dify_file_type(filename, content_type)
                
                # 按照 Dify 官方格式构建文件参数（单个对象，不是数组）
                final_inputs[file_variable_name] = {
                    "type": dify_file_type,
                    "transfer_method": "local_file", 
                    "url": "",
                    "upload_file_id": upload_file_id
                }
                logger.info(f"文件上传成功 (ID: {upload_file_id}, 类型: {dify_file_type})，已添加到输入变量 '{file_variable_name}'")

            except Exception as e:
                self._handle_simple_refund(points_deducted, user_id, points_before, f"Dify文件上传失败: {str(e)}")
                if isinstance(e, HTTPException): raise e
                else: raise HTTPException(status_code=500, detail=f"处理 Dify 文件上传时出错: {str(e)}")

        # 准备 /workflows/run 的请求 (阻塞模式)
        payload = {
            "inputs": final_inputs,
            "response_mode": "blocking", # 改为阻塞模式
            "user": user_id,
        }
        
        headers = { "Authorization": f"Bearer {self.api_token}", "Content-Type": "application/json" }
        workflow_run_url = f"{self.api_url}/workflows/run"

        try:
            async with httpx.AsyncClient(timeout=100.0) as client: # 阻塞模式，增加超时
                response = await client.post(workflow_run_url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Dify 工作流API错误: {response.status_code} - {error_text}")
                    self._handle_simple_refund(points_deducted, user_id, points_before, "工作流API调用失败")
                    
                    try:
                        error_json = response.json()
                        detail_message = error_json.get("message", "Dify API 调用失败")
                    except Exception:
                        detail_message = error_text
                    raise HTTPException(status_code=response.status_code, detail=detail_message)
                
                # 获取响应结果
                response_data = response.json()
                if LoggingConfig.should_log_debug():
                    logger.debug(f"Dify 工作流响应: {response_data}")
                
                # 检查并提取输出内容
                if 'data' in response_data and 'outputs' in response_data['data']:
                    outputs = response_data['data']['outputs']
                    if outputs:
                        if LoggingConfig.should_log_debug():
                            logger.debug(f"工作流输出内容: {outputs}")
                        # 查找文本内容
                        text_content = outputs.get('text') or outputs.get('content') or outputs.get('result') or outputs.get('answer')
                        if text_content:
                            if LoggingConfig.should_log_debug():
                                logger.debug(f"提取到文本内容，长度: {len(str(text_content))}")
                        else:
                            if LoggingConfig.should_log_debug():
                                logger.debug(f"未在outputs中找到文本内容，可用字段: {list(outputs.keys())}")
                
                return response_data

        except httpx.TimeoutException:
            self._handle_simple_refund(points_deducted, user_id, points_before, "工作流API请求超时")
            raise HTTPException(status_code=504, detail="Dify 工作流API请求超时")
        except httpx.RequestError as e:
            self._handle_simple_refund(points_deducted, user_id, points_before, f"工作流API请求错误: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Dify 工作流API请求错误: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            self._handle_simple_refund(points_deducted, user_id, points_before, f"工作流服务错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Dify 工作流服务错误: {str(e)}")

    async def run_workflow_with_json(
        self,
        user_id: str,
        inputs: Dict[str, Any],
        response_mode: str = "blocking"
    ) -> Dict[str, Any]:
        """
        使用 JSON 格式运行 Dify 工作流（适用于已上传文件ID的情况）
        
        Args:
            user_id: 用户ID
            inputs: 包含文件引用的输入参数
            response_mode: 响应模式 ("blocking" 或 "streaming")
            
        Returns:
            工作流执行结果
        """
        self._validate_config()
        
        if self.flow_type != FlowType.WORKFLOW:
            raise HTTPException(status_code=400, detail=f"流 {self.flow_id} 不是工作流类型")

        # 检查并扣除积分（与原方法相同的逻辑）
        points_deducted, points_before = False, 0
        if self.points_service:
            try:
                balance = await self.points_service.get_user_balance(user_id)
                if balance and balance.total_points < self.points_cost:
                    raise HTTPException(status_code=402, detail=f"积分不足，需要 {self.points_cost}，当前: {balance.total_points}")
                
                if balance:
                    points_before = balance.total_points
                    supabase = supabase_service.get_client()
                    new_points = points_before - self.points_cost
                    
                    try:
                        rpc_result = supabase.rpc('update_user_points_bypass_rls', {
                            'p_user_id': user_id,
                            'p_new_points': new_points
                        }).execute()
                        
                        if rpc_result.data:
                            points_deducted = True
                            logger.info(f"JSON工作流调用扣除 {self.points_cost} 积分")
                        else:
                            raise Exception("RPC更新积分失败")
                    except Exception as rpc_error:
                        logger.warning(f"RPC方法更新积分失败: {rpc_error}，尝试直接更新")
                        update_result = supabase.from_("user_profiles").update({
                            "points": new_points
                        }).eq("user_id", user_id).execute()
                        
                        if not update_result.data:
                            raise HTTPException(status_code=500, detail="积分扣除失败")
                        
                        points_deducted = True
                        logger.info(f"JSON工作流调用直接更新成功扣除 {self.points_cost} 积分")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"积分扣除异常: {e}")
                raise HTTPException(status_code=500, detail=f"积分扣除失败: {str(e)}")

        # 准备 JSON 请求到 Dify
        payload = {
            "inputs": inputs,
            "response_mode": response_mode,
            "user": user_id,
        }
        
        headers = { 
            "Authorization": f"Bearer {self.api_token}", 
            "Content-Type": "application/json" 
        }
        workflow_run_url = f"{self.api_url}/workflows/run"

        try:
            timeout = 100.0 if response_mode == "blocking" else 30.0
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(workflow_run_url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Dify JSON工作流API错误: {response.status_code} - {error_text}")
                    self._handle_simple_refund(points_deducted, user_id, points_before, "JSON工作流API调用失败")
                    
                    try:
                        error_json = response.json()
                        detail_message = error_json.get("message", "Dify API 调用失败")
                    except Exception:
                        detail_message = error_text
                    raise HTTPException(status_code=response.status_code, detail=detail_message)
                
                # 获取响应结果
                response_data = response.json()
                logger.info(f"Dify JSON工作流响应: {response_data}")
                
                # 检查并提取输出内容
                if 'data' in response_data and 'outputs' in response_data['data']:
                    outputs = response_data['data']['outputs']
                    if outputs:
                        logger.info(f"JSON工作流输出内容: {outputs}")
                        # 查找文本内容
                        text_content = outputs.get('text') or outputs.get('content') or outputs.get('result') or outputs.get('answer')
                        if text_content:
                            logger.info(f"JSON模式提取到文本内容，长度: {len(str(text_content))}")
                        else:
                            logger.warning(f"JSON模式未在outputs中找到文本内容，可用字段: {list(outputs.keys())}")
                
                return response_data

        except httpx.TimeoutException:
            self._handle_simple_refund(points_deducted, user_id, points_before, "JSON工作流API请求超时")
            raise HTTPException(status_code=504, detail="Dify JSON工作流API请求超时")
        except httpx.RequestError as e:
            self._handle_simple_refund(points_deducted, user_id, points_before, f"JSON工作流API请求错误: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Dify JSON工作流API请求错误: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            self._handle_simple_refund(points_deducted, user_id, points_before, f"JSON工作流服务错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Dify JSON工作流服务错误: {str(e)}")

    async def run_workflow_with_json_stream(
        self,
        user_id: str,
        inputs: Dict[str, Any]
    ) -> AsyncIterator[str]:
        """
        使用 JSON 格式运行 Dify 工作流（流式模式，适用于已上传文件ID的情况）
        
        Args:
            user_id: 用户ID
            inputs: 包含文件引用的输入参数
            
        Yields:
            流式响应数据
        """
        self._validate_config()
        
        if self.flow_type != FlowType.WORKFLOW:
            raise HTTPException(status_code=400, detail=f"流 {self.flow_id} 不是工作流类型")

        # 检查并扣除积分（与原方法相同的逻辑）
        points_deducted, points_before = False, 0
        if self.points_service:
            try:
                balance = await self.points_service.get_user_balance(user_id)
                if balance and balance.total_points < self.points_cost:
                    raise HTTPException(status_code=402, detail=f"积分不足，需要 {self.points_cost}，当前: {balance.total_points}")
                
                if balance:
                    points_before = balance.total_points
                    supabase = supabase_service.get_client()
                    new_points = points_before - self.points_cost
                    
                    try:
                        rpc_result = supabase.rpc('update_user_points_bypass_rls', {
                            'p_user_id': user_id,
                            'p_new_points': new_points
                        }).execute()
                        
                        if rpc_result.data:
                            points_deducted = True
                            logger.info(f"JSON流式工作流调用扣除 {self.points_cost} 积分")
                        else:
                            raise Exception("RPC更新积分失败")
                    except Exception as rpc_error:
                        logger.warning(f"RPC方法更新积分失败: {rpc_error}，尝试直接更新")
                        update_result = supabase.from_("user_profiles").update({
                            "points": new_points
                        }).eq("user_id", user_id).execute()
                        
                        if not update_result.data:
                            raise HTTPException(status_code=500, detail="积分扣除失败")
                        
                        points_deducted = True
                        logger.info(f"JSON流式工作流调用直接更新成功扣除 {self.points_cost} 积分")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"积分扣除异常: {e}")
                raise HTTPException(status_code=500, detail=f"积分扣除失败: {str(e)}")

        # 准备 JSON 请求到 Dify（流式模式）
        payload = {
            "inputs": inputs,
            "response_mode": "streaming",
            "user": user_id,
        }
        
        headers = { 
            "Authorization": f"Bearer {self.api_token}", 
            "Content-Type": "application/json" 
        }
        workflow_run_url = f"{self.api_url}/workflows/run"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                async with client.stream(
                    "POST",
                    workflow_run_url,
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"Dify JSON流式工作流API错误: {response.status_code} - {error_text}")
                        self._handle_simple_refund(points_deducted, user_id, points_before, "JSON流式工作流API调用失败")
                        
                        try:
                            error_json = json.loads(error_text.decode())
                            detail_message = error_json.get("message", "Dify API 调用失败")
                        except Exception:
                            detail_message = error_text.decode()
                        raise HTTPException(status_code=response.status_code, detail=detail_message)
                    
                    # 流式处理响应
                    async for chunk in response.aiter_lines():
                        if chunk.strip():
                            try:
                                # 解析 SSE 格式数据
                                if chunk.startswith("data: "):
                                    data_str = chunk[6:]  # 移除 "data: " 前缀
                                    if data_str.strip() == "[DONE]":
                                        break
                                    
                                    data = json.loads(data_str)
                                    
                                    # 只返回有用的事件
                                    if data.get("event") in ["workflow_started", "node_started", "node_finished", "workflow_finished", "error"]:
                                        yield json.dumps(data)
                                    
                            except json.JSONDecodeError as e:
                                logger.warning(f"解析 Dify JSON流式响应数据失败: {e}, chunk: {chunk}")
                                continue

        except httpx.TimeoutException:
            self._handle_simple_refund(points_deducted, user_id, points_before, "JSON流式工作流API请求超时")
            raise HTTPException(status_code=504, detail="Dify JSON流式工作流API请求超时")
        except httpx.RequestError as e:
            self._handle_simple_refund(points_deducted, user_id, points_before, f"JSON流式工作流API请求错误: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Dify JSON流式工作流API请求错误: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            self._handle_simple_refund(points_deducted, user_id, points_before, f"JSON流式工作流服务错误: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Dify JSON流式工作流服务错误: {str(e)}")

    def _handle_simple_refund(self, points_deducted: bool, user_id: str, points_before: int, reason: str):
        """处理API调用失败时的简单积分退还"""
        if points_deducted and self.points_service:
            try:
                supabase = supabase_service.get_client()
                supabase.from_("user_profiles").update({
                    "points": points_before  # 恢复到原来的积分
                }).eq("user_id", user_id).execute()
                logger.info(f"Dify调用失败，已退还 {self.points_cost} 积分: {reason}")
            except Exception as refund_error:
                logger.error(f"积分退还失败: {refund_error}")
        elif points_deducted and not self.points_service:
            logger.warning(f"积分服务不可用，无法退还积分: {reason}")
    
    async def get_conversation_messages(
        self,
        user_id: str,
        conversation_id: str,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        获取会话历史消息
        
        Args:
            user_id: 用户ID
            conversation_id: 会话ID
            limit: 消息数量限制
            
        Returns:
            会话消息数据
        """
        self._validate_config()
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "user": user_id,
            "limit": limit
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/messages",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"获取会话消息失败: {response.status_code} - {error_text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"获取会话消息失败: {error_text}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"获取会话消息请求错误: {e}")
            raise HTTPException(status_code=502, detail=f"获取会话消息失败: {str(e)}")
    
    async def get_user_conversations(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        获取用户的会话列表
        
        Args:
            user_id: 用户ID
            limit: 会话数量限制
            
        Returns:
            用户会话列表
        """
        self._validate_config()
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "user": user_id,
            "limit": limit
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.api_url}/conversations",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"获取用户会话失败: {response.status_code} - {error_text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"获取用户会话失败: {error_text}"
                    )
                
                return response.json()
                
        except httpx.RequestError as e:
            logger.error(f"获取用户会话请求错误: {e}")
            raise HTTPException(status_code=502, detail=f"获取用户会话失败: {str(e)}")


# 创建全局 Dify 服务实例 (使用默认配置)
dify_service = DifyService()