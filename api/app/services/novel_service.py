"""
小说服务类
基于现有的MaterialService模式实现，支持RLS鉴权
"""

from typing import List, Optional, Dict, Any, Tuple
from app.services.supabase_client import supabase_service
from app.services.novel_segmentation_service import NovelSegmentationService, SegmentationConfig, SegmentationMode
from app.services.epub_service import epub_service, EpubParseResult
from app.schemas.novel_schemas import (
    NovelCreate, NovelUpdate, NovelResponse, NovelListItem, 
    NovelListResponse, PublicNovelItem, PublicNovelListResponse,
    NovelQueryParams, NovelStats, NovelBatchDeleteRequest
)
from app.schemas.novel_segmentation_schemas import SegmentationConfigRequest
from app.schemas.novel_progress_schemas import (
    NovelProgress, NovelProgressResponse, UpdateProgressRequest,
    NovelProgressWithInfo, ReadingStats
)
import structlog
import json
import time
from datetime import datetime
from uuid import UUID

logger = structlog.get_logger()


class NovelService:
    """小说服务类"""
    
    def __init__(self):
        # 使用service role客户端，可以绕过RLS进行必要的系统级操作
        self.service_client = supabase_service.get_client()
        # 初始化分段服务
        self.segmentation_service = NovelSegmentationService()
    
    def _get_user_client(self, access_token: str):
        """获取用户客户端（遵循RLS策略）"""
        if not access_token:
            raise ValueError("此操作需要用户访问令牌。")
        return supabase_service.get_user_client(access_token)
    
    # ================================
    # 小说CRUD操作
    # ================================
    
    async def create_novel(self, user_id: str, novel_data: NovelCreate, access_token: str = None) -> NovelResponse:
        """创建小说"""
        try:
            # 准备数据
            data = {
                "user_id": user_id,
                "title": novel_data.title,
                "author": novel_data.author,
                "description": novel_data.description,
                "language": novel_data.language,
                "is_public": novel_data.is_public,
                "cover_image_url": novel_data.cover_image_url,
                "original_filename": novel_data.original_filename,
                "total_chapters": 0
            }
            
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            response = client.table("novels").insert(data).execute()
            
            if response.data and len(response.data) > 0:
                novel_dict = response.data[0]
                logger.info("Novel created successfully", novel_id=novel_dict["id"], user_id=user_id)
                return NovelResponse(**novel_dict)
            else:
                raise Exception("Failed to create novel - no data returned")
                
        except Exception as e:
            logger.error(f"Error creating novel: {e}", user_id=user_id)
            raise
    
    async def get_novel(self, novel_id: str, user_id: str = None, access_token: str = None) -> Optional[NovelResponse]:
        """获取单个小说详情"""
        try:
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            response = client.table("novels").select("*").eq("id", novel_id).execute()
            
            if response.data and len(response.data) > 0:
                novel_dict = response.data[0]
                # 额外权限检查（虽然RLS已经处理，但作为双重保障）
                if user_id and novel_dict["user_id"] != user_id and not novel_dict["is_public"]:
                    logger.warning("User trying to access unauthorized novel", 
                                 user_id=user_id, novel_id=novel_id)
                    return None
                
                return NovelResponse(**novel_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error getting novel: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    async def update_novel(self, novel_id: str, user_id: str, novel_data: NovelUpdate, 
                          access_token: str = None) -> Optional[NovelResponse]:
        """更新小说信息"""
        try:
            # 准备更新数据（过滤None值）
            update_data = {}
            for field, value in novel_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            
            if not update_data:
                raise ValueError("No fields to update")
            
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            response = client.table("novels").update(update_data).eq("id", novel_id).execute()
            
            if response.data and len(response.data) > 0:
                novel_dict = response.data[0]
                logger.info("Novel updated successfully", novel_id=novel_id, user_id=user_id)
                return NovelResponse(**novel_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error updating novel: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    async def delete_novel(self, novel_id: str, user_id: str, access_token: str = None) -> bool:
        """删除小说（包括存储桶中的文件）"""
        try:
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            # 首先获取小说信息，确保它存在且用户有权限删除
            novel_response = client.table("novels").select("*").eq("id", novel_id).execute()
            
            if not novel_response.data or len(novel_response.data) == 0:
                logger.warning("Novel not found for deletion", novel_id=novel_id, user_id=user_id)
                return False
            
            novel = novel_response.data[0]
            
            # 额外权限检查（确保只有小说所有者可以删除）
            if novel["user_id"] != user_id:
                logger.warning("User attempting to delete unauthorized novel", 
                             novel_id=novel_id, user_id=user_id, owner_id=novel["user_id"])
                return False
            
            # 删除存储桶中的文件夹和文件
            try:
                await self._delete_novel_storage_files(user_id, novel_id)
                logger.info("Novel storage files deleted successfully", novel_id=novel_id, user_id=user_id)
            except Exception as storage_error:
                logger.warning(f"Failed to delete storage files, but continuing with database deletion: {storage_error}", 
                             novel_id=novel_id, user_id=user_id)
                # 继续执行数据库删除，即使存储文件删除失败
            
            # 删除数据库记录
            delete_response = client.table("novels").delete().eq("id", novel_id).execute()
            
            success = bool(delete_response.data)
            if success:
                logger.info("Novel deleted successfully", novel_id=novel_id, user_id=user_id)
            else:
                logger.warning("Novel deletion failed - no rows affected", 
                             novel_id=novel_id, user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting novel: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    async def _delete_novel_storage_files(self, user_id: str, novel_id: str) -> None:
        """删除小说在存储桶中的所有文件"""
        try:
            # 列出用户小说文件夹中的所有文件
            folder_path = f"{user_id}/{novel_id}"
            
            # 获取文件夹中的所有文件
            response = self.service_client.storage.from_("novel").list(folder_path)
            
            if response and len(response) > 0:
                # 构建需要删除的文件路径列表
                files_to_delete = []
                for file_info in response:
                    file_path = f"{folder_path}/{file_info['name']}"
                    files_to_delete.append(file_path)
                
                if files_to_delete:
                    # 批量删除文件
                    delete_response = self.service_client.storage.from_("novel").remove(files_to_delete)
                    logger.info(f"Deleted {len(files_to_delete)} files from storage", 
                              user_id=user_id, novel_id=novel_id, files=files_to_delete)
                else:
                    logger.info("No files found to delete in storage", user_id=user_id, novel_id=novel_id)
            else:
                logger.info("Novel folder not found in storage or already empty", 
                          user_id=user_id, novel_id=novel_id)
                
        except Exception as e:
            logger.error(f"Error deleting novel storage files: {e}", user_id=user_id, novel_id=novel_id)
            raise
    
    # ================================
    # 小说列表查询
    # ================================
    
    async def list_user_novels(self, user_id: str, query: NovelQueryParams, 
                              access_token: str = None) -> NovelListResponse:
        """获取用户小说列表"""
        try:
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            # 构建查询
            query_builder = client.table("novels").select("*", count="exact")
            
            # 用户权限过滤：只能看到自己的小说
            query_builder = query_builder.eq("user_id", user_id)
            
            # 应用过滤条件
            if query.search:
                query_builder = query_builder.or_(
                    f"title.ilike.%{query.search}%,author.ilike.%{query.search}%"
                )
            if query.language:
                query_builder = query_builder.eq("language", query.language)
            if query.is_public is not None:
                query_builder = query_builder.eq("is_public", query.is_public)
            
            # 分页
            offset = (query.page - 1) * query.page_size
            query_builder = query_builder.range(offset, offset + query.page_size - 1)
            
            # 排序
            order_desc = query.sort_order == "desc"
            query_builder = query_builder.order(query.sort_by, desc=order_desc)
            
            response = query_builder.execute()
            
            novels = [NovelListItem(**item) for item in response.data]
            total = response.count or 0
            
            return NovelListResponse(
                novels=novels,
                total=total,
                page=query.page,
                page_size=query.page_size
            )
            
        except Exception as e:
            logger.error(f"Error listing user novels: {e}", user_id=user_id)
            raise
    
    async def list_public_novels(self, query: NovelQueryParams) -> PublicNovelListResponse:
        """获取公开小说列表"""
        try:
            # 使用RLS绕过函数或直接查询
            response = self.service_client.rpc(
                "get_public_novels_bypass_rls"
            ).execute()
            
            if not response.data:
                return PublicNovelListResponse(
                    novels=[],
                    total=0,
                    page=query.page,
                    page_size=query.page_size
                )
            
            # 应用搜索和过滤
            novels_data = response.data
            
            # 搜索过滤
            if query.search:
                search_lower = query.search.lower()
                novels_data = [
                    novel for novel in novels_data
                    if (search_lower in (novel.get("title") or "").lower() or
                        search_lower in (novel.get("author") or "").lower())
                ]
            
            # 语言过滤
            if query.language:
                novels_data = [
                    novel for novel in novels_data
                    if novel.get("language") == query.language
                ]
            
            # 排序
            if query.sort_by == "created_at":
                novels_data.sort(
                    key=lambda x: x.get("created_at", ""),
                    reverse=(query.sort_order == "desc")
                )
            elif query.sort_by == "title":
                novels_data.sort(
                    key=lambda x: x.get("title", "").lower(),
                    reverse=(query.sort_order == "desc")
                )
            
            # 分页
            total = len(novels_data)
            start_idx = (query.page - 1) * query.page_size
            end_idx = start_idx + query.page_size
            paginated_data = novels_data[start_idx:end_idx]
            
            novels = [PublicNovelItem(**item) for item in paginated_data]
            
            return PublicNovelListResponse(
                novels=novels,
                total=total,
                page=query.page,
                page_size=query.page_size
            )
            
        except Exception as e:
            logger.error(f"Error listing public novels: {e}")
            raise
    
    # ================================
    # 批量操作
    # ================================
    
    async def batch_delete_novels(self, user_id: str, novel_ids: List[str], 
                                 access_token: str = None) -> Tuple[int, List[str]]:
        """批量删除小说（包括存储桶中的文件）"""
        try:
            deleted_count = 0
            failed_ids = []
            
            for novel_id in novel_ids:
                try:
                    # 使用单个删除函数，确保存储文件也被删除
                    success = await self.delete_novel(novel_id, user_id, access_token)
                    if success:
                        deleted_count += 1
                        logger.info("Novel deleted in batch", novel_id=novel_id, user_id=user_id)
                    else:
                        failed_ids.append(novel_id)
                        logger.warning("Novel deletion failed in batch", 
                                     novel_id=novel_id, user_id=user_id)
                except Exception as e:
                    failed_ids.append(novel_id)
                    logger.error(f"Error deleting novel in batch: {e}", 
                               novel_id=novel_id, user_id=user_id)
            
            return deleted_count, failed_ids
            
        except Exception as e:
            logger.error(f"Error in batch delete novels: {e}", user_id=user_id)
            raise
    
    # ================================
    # 统计信息
    # ================================
    
    async def get_user_novel_stats(self, user_id: str, access_token: str = None) -> NovelStats:
        """获取用户小说统计信息"""
        try:
            # 使用RLS绕过函数获取用户小说
            response = self.service_client.rpc(
                "get_user_novels_bypass_rls",
                {"p_user_id": user_id}
            ).execute()
            
            novels = response.data or []
            
            # 计算统计信息
            total_novels = len(novels)
            public_novels = sum(1 for novel in novels if novel.get("is_public", False))
            private_novels = total_novels - public_novels
            total_chapters = sum(novel.get("total_chapters", 0) for novel in novels)
            
            # 按语言分组统计
            by_language = {}
            for novel in novels:
                lang = novel.get("language", "unknown")
                by_language[lang] = by_language.get(lang, 0) + 1
            
            return NovelStats(
                total_novels=total_novels,
                public_novels=public_novels,
                private_novels=private_novels,
                total_chapters=total_chapters,
                by_language=by_language
            )
            
        except Exception as e:
            logger.error(f"Error getting user novel stats: {e}", user_id=user_id)
            raise
    
    # ================================
    # 辅助方法
    # ================================
    
    async def update_novel_chapter_count(self, novel_id: str, chapter_count: int) -> bool:
        """更新小说章节数（系统级操作）"""
        try:
            # 使用RLS绕过函数进行系统级更新
            response = self.service_client.rpc(
                "update_novel_chapter_count_bypass_rls",
                {"p_novel_id": novel_id, "p_chapter_count": chapter_count}
            ).execute()
            
            success = bool(response.data)
            if success:
                logger.info("Novel chapter count updated", 
                          novel_id=novel_id, chapter_count=chapter_count)
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating novel chapter count: {e}", 
                       novel_id=novel_id, chapter_count=chapter_count)
            raise
    
    async def check_novel_ownership(self, novel_id: str, user_id: str) -> bool:
        """检查小说所有权"""
        try:
            response = self.service_client.table("novels").select("user_id").eq("id", novel_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]["user_id"] == user_id
            return False
            
        except Exception as e:
            logger.error(f"Error checking novel ownership: {e}", 
                       novel_id=novel_id, user_id=user_id)
            return False
    
    async def toggle_novel_public_status(self, novel_id: str, user_id: str, 
                                       is_public: bool, access_token: str = None) -> Optional[NovelResponse]:
        """切换小说公开状态"""
        try:
            update_data = {"is_public": is_public}
            
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            response = client.table("novels").update(update_data).eq("id", novel_id).execute()
            
            if response.data and len(response.data) > 0:
                novel_dict = response.data[0]
                logger.info("Novel public status toggled", 
                          novel_id=novel_id, user_id=user_id, is_public=is_public)
                return NovelResponse(**novel_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error toggling novel public status: {e}", 
                       novel_id=novel_id, user_id=user_id)
            raise

    # ================================
    # 小说分段相关方法
    # ================================
    
    async def upload_novel_file(self, user_id: str, novel_id: str, file_content: bytes, access_token: str, filename: str = None) -> str:
        """上传小说文件到存储桶"""
        try:
            # 验证输入参数
            if not isinstance(file_content, bytes):
                if isinstance(file_content, str):
                    file_content = file_content.encode('utf-8')
                else:
                    raise ValueError(f"文件内容类型错误，期望 bytes 或 str，得到 {type(file_content)}")
            
            if len(file_content) == 0:
                raise ValueError("文件内容为空")
            
            # 使用用户客户端确保RLS策略生效
            user_client = self._get_user_client(access_token)
            
            # 验证用户对该小说的权限
            novel_response = user_client.table("novels").select("user_id").eq("id", novel_id).execute()
            
            if not novel_response.data or len(novel_response.data) == 0:
                raise ValueError("小说不存在")
            
            novel = novel_response.data[0]
            if novel["user_id"] != user_id:
                raise ValueError("无权上传文件到此小说")
            
            # 检查文件类型并处理
            is_epub = filename and filename.lower().endswith('.epub')
            if is_epub:
                # EPUB文件：先解析提取文本，然后保存原文件和文本版本
                try:
                    epub_result = await epub_service.parse_epub_file(file_content)
                    
                    # 验证EPUB解析结果
                    if not epub_result.chapters:
                        raise ValueError("EPUB文件解析成功但未找到任何章节内容")
                    
                    # 保存原始EPUB文件
                    epub_storage_path = f"{user_id}/{novel_id}/original.epub"
                    await self._upload_file_to_storage(user_client, epub_storage_path, file_content, "application/epub+zip")
                    
                    # 转换章节为文本格式并验证结果
                    text_content = epub_service.convert_to_segmentation_format(epub_result.chapters)
                    
                    # 验证转换后的文本内容
                    if not text_content or text_content.strip() == "":
                        raise ValueError("EPUB章节转换为文本后内容为空")
                    
                    # 检查文本内容是否包含二进制数据（这应该不会发生）
                    try:
                        # 尝试编码为UTF-8，如果包含二进制数据会失败
                        text_bytes = text_content.encode('utf-8')
                        # 再次解码验证
                        text_content.encode('utf-8').decode('utf-8')
                    except UnicodeEncodeError as e:
                        logger.error(f"Text content contains invalid characters: {e}")
                        raise ValueError("转换的文本内容包含无法编码的字符")
                    
                    # 保存处理后的文本版本
                    text_storage_path = f"{user_id}/{novel_id}/original.txt"
                    await self._upload_file_to_storage(user_client, text_storage_path, text_bytes, "text/plain")
                    
                    # 更新小说元数据（如果EPUB中有更好的信息）
                    await self._update_novel_from_epub_metadata(novel_id, user_id, epub_result.metadata, access_token)
                    
                    logger.info(f"EPUB file processed and uploaded successfully", 
                               novel_id=novel_id, user_id=user_id, 
                               chapters_count=len(epub_result.chapters),
                               text_length=len(text_content),
                               warnings_count=len(epub_result.warnings))
                    
                    return text_storage_path  # 返回文本版本路径用于后续分段处理
                    
                except Exception as epub_error:
                    logger.error(f"EPUB processing failed: {epub_error}", 
                               novel_id=novel_id, user_id=user_id)
                    raise ValueError(f"EPUB文件处理失败: {str(epub_error)}")
            else:
                # TXT文件：直接保存
                storage_path = f"{user_id}/{novel_id}/original.txt"
                await self._upload_file_to_storage(user_client, storage_path, file_content, "text/plain")
                return storage_path
            
        except Exception as e:
            logger.error(f"Error uploading novel file: {e}", 
                       novel_id=novel_id, user_id=user_id)
            raise
    
    async def _upload_file_to_storage(self, client, storage_path: str, file_content: bytes, content_type: str) -> None:
        """上传文件到Supabase Storage的通用方法"""
        try:
            # 先尝试删除现有文件（如果存在）
            try:
                client.storage.from_("novel").remove([storage_path])
            except:
                pass  # 忽略删除错误，文件可能不存在
            
            # 上传新文件
            response = client.storage.from_("novel").upload(
                storage_path,
                file_content,
                file_options={
                    "content-type": f"{content_type}; charset=utf-8" if content_type.startswith("text") else content_type,
                    "cache-control": "3600"
                }
            )
            
            # 检查上传响应
            if response is None:
                raise Exception("Upload failed: response is empty")
            
            # 检查是否有错误
            if hasattr(response, 'error') and response.error:
                error_msg = str(response.error) if response.error else "Unknown upload error"
                raise Exception(f"Storage upload failed: {error_msg}")
            
            # 检查响应数据
            if hasattr(response, 'data') and not response.data:
                raise Exception("Upload failed: no response data")
                
        except Exception as upload_error:
            logger.error(f"Error uploading file to storage: {upload_error}", storage_path=storage_path)
            raise Exception(f"文件上传失败: {str(upload_error)}")
    
    async def _update_novel_from_epub_metadata(self, novel_id: str, user_id: str, epub_metadata, access_token: str) -> None:
        """根据EPUB元数据更新小说信息"""
        try:
            # 只有当EPUB元数据比现有数据更完整时才更新
            update_data = {}
            
            if epub_metadata.author and epub_metadata.author.strip():
                update_data["author"] = epub_metadata.author.strip()
            
            if epub_metadata.description and epub_metadata.description.strip():
                update_data["description"] = epub_metadata.description.strip()
            
            if epub_metadata.language and epub_metadata.language != "en":
                update_data["language"] = epub_metadata.language
            
            if update_data:
                client = self._get_user_client(access_token)
                response = client.table("novels").update(update_data).eq("id", novel_id).execute()
                
                if response.data:
                    logger.info("Updated novel metadata from EPUB", novel_id=novel_id, updates=update_data)
        
        except Exception as e:
            logger.warning(f"Failed to update novel metadata from EPUB: {e}", novel_id=novel_id)

    async def get_novel_content_from_storage(self, novel_id: str, user_id: str) -> str:
        """从存储中获取小说内容"""
        try:
            # 获取小说信息验证权限
            novel_response = self.service_client.table("novels").select("user_id").eq("id", novel_id).execute()
            
            if not novel_response.data or len(novel_response.data) == 0:
                raise ValueError("小说不存在")
            
            novel = novel_response.data[0]
            
            # 检查权限
            if novel["user_id"] != user_id:
                raise ValueError("无权访问此小说")
            
            # 动态生成存储路径：userid/novelid/original.txt
            storage_path = f"{user_id}/{novel_id}/original.txt"
            
            # 从 Supabase Storage 下载文件
            response = self.service_client.storage.from_("novel").download(storage_path)
            
            if not response:
                # 如果original.txt不存在，检查是否有EPUB文件需要重新处理
                epub_path = f"{user_id}/{novel_id}/original.epub"
                try:
                    epub_response = self.service_client.storage.from_("novel").download(epub_path)
                    if epub_response:
                        logger.warning(f"original.txt not found but EPUB exists, may need reprocessing", 
                                     novel_id=novel_id, user_id=user_id)
                        raise ValueError("小说文件需要重新处理，请重新上传EPUB文件")
                except:
                    pass
                raise ValueError("无法读取小说文件")
            
            # 检查文件内容是否为二进制数据（EPUB文件被错误保存为txt）
            if len(response) > 4 and response[:2] == b'PK':
                logger.warning(f"original.txt contains EPUB binary data, attempting automatic reprocessing", 
                             novel_id=novel_id, user_id=user_id)
                
                # 尝试自动重新处理EPUB文件
                try:
                    # 使用EPUB内容重新处理
                    epub_result = await epub_service.parse_epub_file(response)
                    
                    if not epub_result.chapters:
                        raise ValueError("EPUB重新解析后未找到任何章节内容")
                    
                    # 转换章节为文本格式
                    text_content = epub_service.convert_to_segmentation_format(epub_result.chapters)
                    
                    if not text_content or text_content.strip() == "":
                        raise ValueError("EPUB章节转换为文本后内容为空")
                    
                    # 保存处理后的文本版本（覆盖错误的二进制内容）
                    text_bytes = text_content.encode('utf-8')
                    await self._upload_file_to_storage(
                        self.service_client, 
                        storage_path, 
                        text_bytes, 
                        "text/plain"
                    )
                    
                    # 同时保存正确的EPUB文件到对应路径
                    epub_path = f"{user_id}/{novel_id}/original.epub"
                    await self._upload_file_to_storage(
                        self.service_client,
                        epub_path,
                        response,
                        "application/epub+zip"
                    )
                    
                    logger.info(f"Successfully reprocessed legacy EPUB file", 
                              novel_id=novel_id, user_id=user_id,
                              chapters_count=len(epub_result.chapters),
                              text_length=len(text_content))
                    
                    # 返回重新处理后的文本内容
                    return text_content
                    
                except Exception as reprocess_error:
                    logger.error(f"Failed to reprocess EPUB file: {reprocess_error}", 
                               novel_id=novel_id, user_id=user_id)
                    raise ValueError(f"小说文件格式错误，自动重新处理失败: {str(reprocess_error)}。请手动重新上传EPUB文件")
            
            # 尝试多种编码来解析文本内容
            encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin-1']
            content = None
            
            for encoding in encodings:
                try:
                    content = response.decode(encoding)
                    logger.info(f"Successfully decoded file with encoding: {encoding}", 
                              novel_id=novel_id, user_id=user_id)
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                raise ValueError(f"无法使用常见的编码格式({', '.join(encodings)})解码文件内容")

            return content
            
        except Exception as e:
            logger.error(f"Error getting novel content from storage: {e}", 
                       novel_id=novel_id, user_id=user_id)
            raise
    
    async def preview_novel_segmentation(self, novel_id: str, user_id: str, 
                                       config_request: SegmentationConfigRequest,
                                       max_segments: int = 5) -> Dict[str, Any]:
        """预览小说分段效果"""
        try:
            logger.info("Previewing novel segmentation", 
                       novel_id=novel_id, user_id=user_id, config=config_request.model_dump())
            
            content = await self.get_novel_content_from_storage(novel_id, user_id)
            
            segmentation_config = SegmentationConfig(
                primary_segmentation_mode=config_request.primary_segmentation_mode,
                secondary_segmentation_mode=config_request.secondary_segmentation_mode,
                max_chars_per_segment=config_request.max_chars_per_segment,
                language=config_request.language,
                custom_regex_separators=config_request.custom_regex_separators,
                characters_per_segment=config_request.characters_per_segment,
                paragraphs_per_segment=config_request.paragraphs_per_segment,
                sentences_per_segment=config_request.sentences_per_segment
            )
            
            preview_result = await self.segmentation_service.preview_segmentation(
                content, segmentation_config, max_segments
            )
            
            result = {
                "total_segments": preview_result["total_segments"],
                "preview_segments": preview_result["preview_segments"],
                "warnings": preview_result["warnings"],
                "config": config_request.model_dump()
            }
            
            logger.info("Novel segmentation preview completed", 
                       novel_id=novel_id, total_segments=preview_result["total_segments"],
                       warnings_count=len(preview_result["warnings"]))
            
            return result
            
        except Exception as e:
            logger.error(f"Error previewing novel segmentation: {e}", 
                       novel_id=novel_id, user_id=user_id)
            raise
    
    async def segment_novel(self, novel_id: str, user_id: str, 
                           config_request: SegmentationConfigRequest) -> Dict[str, Any]:
        """执行小说分段，将分段保存到数据库"""
        try:
            start_time = time.time()
            logger.info("Starting novel segmentation", 
                       novel_id=novel_id, user_id=user_id, config=config_request.model_dump())
            
            content = await self.get_novel_content_from_storage(novel_id, user_id)
            
            segmentation_config = SegmentationConfig(
                primary_segmentation_mode=config_request.primary_segmentation_mode,
                secondary_segmentation_mode=config_request.secondary_segmentation_mode,
                max_chars_per_segment=config_request.max_chars_per_segment,
                language=config_request.language,
                custom_regex_separators=config_request.custom_regex_separators,
                characters_per_segment=config_request.characters_per_segment,
                paragraphs_per_segment=config_request.paragraphs_per_segment,
                sentences_per_segment=config_request.sentences_per_segment
            )
            
            segmentation_result = await self.segmentation_service.segment_text(content, segmentation_config)
            
            await self._delete_existing_chapters(novel_id)
            
            await self._save_segments_to_database(novel_id, segmentation_result.segments, segmentation_config)
            
            await self.update_novel_chapter_count(novel_id, len(segmentation_result.segments))
            
            await self._save_segmentation_config(novel_id, config_request)
            
            end_time = time.time()
            processing_time = round(end_time - start_time, 2)
            
            result = {
                "novel_id": novel_id,
                "total_segments": len(segmentation_result.segments),
                "total_chapters": len(segmentation_result.segments),
                "warnings": segmentation_result.warnings,
                "processing_time": processing_time,
                "config": config_request.model_dump()
            }
            
            logger.info("Novel segmentation completed", 
                       novel_id=novel_id, total_segments=len(segmentation_result.segments), 
                       processing_time=processing_time,
                       warnings_count=len(segmentation_result.warnings))
            
            return result
            
        except Exception as e:
            logger.error(f"Error segmenting novel: {e}", 
                       novel_id=novel_id, user_id=user_id)
            raise
    
    async def get_novel_segmentation_stats(self, novel_id: str, user_id: str) -> Dict[str, Any]:
        """获取小说分段统计信息"""
        try:
            # 检查权限
            if not await self.check_novel_ownership(novel_id, user_id):
                raise ValueError("无权访问此小说")
            
            # 获取章节信息
            chapters_response = self.service_client.table("novel_chapters").select(
                "id, title, char_count, paragraph_count, sentence_count"
            ).eq("novel_id", novel_id).order("order", desc=False).execute()
            
            if not chapters_response.data:
                raise ValueError("小说尚未分段")
            
            chapters = chapters_response.data
            total_chapters = len(chapters)
            
            # 计算统计信息
            total_characters = sum(ch.get("char_count", 0) for ch in chapters)
            average_chapter_length = total_characters // total_chapters if total_chapters > 0 else 0
            
            chapter_lengths = [ch.get("char_count", 0) for ch in chapters]
            shortest_chapter = min(chapter_lengths) if chapter_lengths else 0
            longest_chapter = max(chapter_lengths) if chapter_lengths else 0
            
            # 获取分段配置
            novel_response = self.service_client.table("novels").select(
                "segmentation_config"
            ).eq("id", novel_id).execute()
            
            segmentation_config = {}
            if novel_response.data and novel_response.data[0].get("segmentation_config"):
                segmentation_config = novel_response.data[0]["segmentation_config"]
            
            result = {
                "novel_id": novel_id,
                "total_chapters": total_chapters,
                "total_characters": total_characters,
                "average_chapter_length": average_chapter_length,
                "shortest_chapter": shortest_chapter,
                "longest_chapter": longest_chapter,
                "segmentation_config": segmentation_config
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting novel segmentation stats: {e}", 
                       novel_id=novel_id, user_id=user_id)
            raise
    
    async def _delete_existing_chapters(self, novel_id: str) -> None:
        """删除现有章节"""
        try:
            response = self.service_client.table("novel_chapters").delete().eq("novel_id", novel_id).execute()
            logger.info("Deleted existing chapters", novel_id=novel_id)
            
        except Exception as e:
            logger.error(f"Error deleting existing chapters: {e}", novel_id=novel_id)
            raise
    
    async def _save_segments_to_database(self, novel_id: str, segments: List, 
                                        config: SegmentationConfig) -> None:
        """将分段保存到数据库"""
        try:
            # 准备章节数据
            chapters_data = []
            for segment in segments:
                chapter_data = {
                    "novel_id": novel_id,
                    "chapter_number": segment.order + 1,
                    "title": segment.title,
                    "content": segment.content,
                    "order": segment.order,
                    "char_count": segment.char_count,
                    "paragraph_count": segment.paragraph_count,
                    "sentence_count": segment.sentence_count
                }
                chapters_data.append(chapter_data)
            
            # 批量插入章节
            response = self.service_client.table("novel_chapters").insert(chapters_data).execute()
            
            logger.info("Saved segments to database", 
                       novel_id=novel_id, chapter_count=len(chapters_data))
            
        except Exception as e:
            logger.error(f"Error saving segments to database: {e}", novel_id=novel_id)
            raise
    
    async def _save_segmentation_config(self, novel_id: str, 
                                      config_request: SegmentationConfigRequest) -> None:
        """保存分段配置到小说记录"""
        try:
            config_data = {
                "primary_segmentation_mode": config_request.primary_segmentation_mode.value,
                "secondary_segmentation_mode": config_request.secondary_segmentation_mode.value if config_request.secondary_segmentation_mode else None,
                "max_chars_per_segment": config_request.max_chars_per_segment,
                "language": config_request.language,
                "characters_per_segment": config_request.characters_per_segment,
                "paragraphs_per_segment": config_request.paragraphs_per_segment,
                "sentences_per_segment": config_request.sentences_per_segment,
                "custom_regex_separators": config_request.custom_regex_separators
            }
            
            update_data = {"segmentation_config": config_data}
            
            response = self.service_client.table("novels").update(update_data).eq("id", novel_id).execute()
            
            logger.info("Saved segmentation config", novel_id=novel_id)
            
        except Exception as e:
            logger.error(f"Error saving segmentation config: {e}", novel_id=novel_id)
            raise
    
    async def get_novel_segments(self, novel_id: str, user_id: str = None, 
                               page: int = 1, page_size: int = 100, 
                               access_token: str = None) -> Tuple[List[Dict], int]:
        """获取小说分段列表"""
        try:
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            # 首先验证用户是否有权限访问该小说
            novel = await self.get_novel(novel_id, user_id, access_token)
            if not novel:
                raise Exception("小说不存在或无权访问")
            
            # 计算偏移量
            offset = (page - 1) * page_size
            
            # 获取总数
            count_response = client.table("novel_chapters").select("id", count="exact").eq("novel_id", novel_id).execute()
            total = count_response.count if count_response.count else 0
            
            # 获取分段数据
            response = client.table("novel_chapters").select(
                "id, chapter_number, title, content, order, char_count, paragraph_count, sentence_count, created_at"
            ).eq("novel_id", novel_id).order("order", desc=False).range(offset, offset + page_size - 1).execute()
            
            segments = []
            if response.data:
                for chapter in response.data:
                    segments.append({
                        "id": chapter["id"],
                        "order": chapter["order"],
                        "chapter_number": chapter["chapter_number"],
                        "title": chapter["title"],
                        "content": chapter["content"],
                        "char_count": chapter["char_count"],
                        "paragraph_count": chapter["paragraph_count"],
                        "sentence_count": chapter["sentence_count"],
                        "created_at": chapter["created_at"]
                    })
            
            logger.info("Retrieved novel segments", 
                       novel_id=novel_id, user_id=user_id, 
                       segments_count=len(segments), total=total)
            
            return segments, total
            
        except Exception as e:
            logger.error(f"Error getting novel segments: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    # ================================
    # 阅读进度管理方法
    # ================================
    
    async def get_user_novel_progress(self, novel_id: str, user_id: str, 
                                     access_token: str = None) -> Optional[NovelProgressResponse]:
        """获取用户在特定小说中的阅读进度"""
        try:
            client = self._get_user_client(access_token)
            
            response = client.table("user_novel_progress")\
                .select("*")\
                .eq("novel_id", novel_id)\
                .eq("user_id", user_id)\
                .execute()
            
            if response.data and len(response.data) > 0:
                progress_dict = response.data[0]
                logger.info("Retrieved user novel progress", 
                           novel_id=novel_id, user_id=user_id, 
                           progress=progress_dict["progress_percentage"])
                return NovelProgressResponse(**progress_dict)
            
            logger.info("No progress found for user novel", novel_id=novel_id, user_id=user_id)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user novel progress: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    async def update_user_novel_progress(self, novel_id: str, user_id: str, 
                                        progress_data: UpdateProgressRequest,
                                        access_token: str = None) -> NovelProgressResponse:
        """更新或创建用户在特定小说中的阅读进度"""
        try:
            # 直接使用 service_client 绕过 RLS，避免歧义问题
            client = self.service_client
            
            # 先检查是否存在记录
            existing_response = client.from_("user_novel_progress").select("*").eq("user_id", user_id).eq("novel_id", novel_id).execute()
            
            current_time = datetime.utcnow().isoformat()
            
            progress_record = {
                "user_id": user_id,
                "novel_id": novel_id,
                "last_read_chapter_id": str(progress_data.last_read_chapter_id) if progress_data.last_read_chapter_id else None,
                "last_read_segment_id": progress_data.last_read_segment_id,
                "progress_percentage": progress_data.progress_percentage,
                "last_read_at": current_time
            }
            
            if existing_response.data and len(existing_response.data) > 0:
                # 更新现有记录
                progress_record["updated_at"] = current_time
                response = client.from_("user_novel_progress").update(progress_record).eq("user_id", user_id).eq("novel_id", novel_id).execute()
            else:
                # 创建新记录
                progress_record["created_at"] = current_time
                progress_record["updated_at"] = current_time
                response = client.from_("user_novel_progress").insert(progress_record).execute()
            
            if response.data and len(response.data) > 0:
                progress_dict = response.data[0]
                logger.info("Updated user novel progress using service role", 
                           novel_id=novel_id, user_id=user_id, 
                           progress=progress_dict["progress_percentage"],
                           segment=progress_dict.get("last_read_segment_id"))
                return NovelProgressResponse(**progress_dict)
            else:
                raise Exception("Failed to update progress - no data returned")
                
        except Exception as e:
            logger.error(f"Error updating user novel progress: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    async def get_user_all_novel_progress(self, user_id: str, 
                                         access_token: str = None) -> List[NovelProgressResponse]:
        """获取用户所有小说的阅读进度"""
        try:
            client = self._get_user_client(access_token)
            
            response = client.table("user_novel_progress")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("last_read_at", desc=True)\
                .execute()
            
            progress_list = []
            if response.data:
                for progress_dict in response.data:
                    progress_list.append(NovelProgressResponse(**progress_dict))
            
            logger.info("Retrieved user all novel progress", 
                       user_id=user_id, count=len(progress_list))
            return progress_list
            
        except Exception as e:
            logger.error(f"Error getting user all novel progress: {e}", user_id=user_id)
            raise
    
    async def get_user_novel_progress_with_info(self, user_id: str, 
                                               access_token: str = None) -> List[NovelProgressWithInfo]:
        """获取用户所有小说的阅读进度（包含小说信息）"""
        try:
            client = self._get_user_client(access_token)
            
            # 联表查询获取进度和小说信息
            response = client.table("user_novel_progress")\
                .select("""
                    *,
                    novels!user_novel_progress_novel_id_fkey(
                        title,
                        author,
                        cover_image_url,
                        language,
                        total_chapters
                    )
                """)\
                .eq("user_id", user_id)\
                .order("last_read_at", desc=True)\
                .execute()
            
            progress_list = []
            if response.data:
                for item in response.data:
                    novel_info = item.get("novels", {})
                    if novel_info:  # 确保小说信息存在
                        progress_with_info = NovelProgressWithInfo(
                            **item,
                            novel_title=novel_info.get("title", ""),
                            novel_author=novel_info.get("author"),
                            novel_cover_image_url=novel_info.get("cover_image_url"),
                            novel_language=novel_info.get("language", ""),
                            novel_total_chapters=novel_info.get("total_chapters", 0)
                        )
                        progress_list.append(progress_with_info)
            
            logger.info("Retrieved user novel progress with info", 
                       user_id=user_id, count=len(progress_list))
            return progress_list
            
        except Exception as e:
            logger.error(f"Error getting user novel progress with info: {e}", user_id=user_id)
            raise
    
    async def delete_user_novel_progress(self, novel_id: str, user_id: str, 
                                        access_token: str = None) -> bool:
        """删除用户在特定小说中的阅读进度"""
        try:
            client = self._get_user_client(access_token)
            
            response = client.table("user_novel_progress")\
                .delete()\
                .eq("novel_id", novel_id)\
                .eq("user_id", user_id)\
                .execute()
            
            success = response.data is not None
            if success:
                logger.info("Deleted user novel progress", novel_id=novel_id, user_id=user_id)
            else:
                logger.warning("No progress to delete", novel_id=novel_id, user_id=user_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting user novel progress: {e}", novel_id=novel_id, user_id=user_id)
            raise
    
    async def get_user_reading_stats(self, user_id: str, 
                                    access_token: str = None) -> ReadingStats:
        """获取用户阅读统计信息"""
        try:
            client = self._get_user_client(access_token)
            
            # 获取所有进度记录
            response = client.table("user_novel_progress")\
                .select("*")\
                .eq("user_id", user_id)\
                .execute()
            
            progress_list = response.data or []
            total_novels = len(progress_list)
            
            if total_novels == 0:
                return ReadingStats(
                    total_novels=0,
                    novels_in_progress=0,
                    novels_completed=0,
                    total_reading_time_minutes=0,
                    average_progress=0.0,
                    last_read_novel_id=None,
                    last_read_at=None
                )
            
            # 计算统计信息
            novels_in_progress = len([p for p in progress_list if 0 < p["progress_percentage"] < 100])
            novels_completed = len([p for p in progress_list if p["progress_percentage"] >= 100])
            average_progress = sum(p["progress_percentage"] for p in progress_list) / total_novels
            
            # 找到最近阅读的小说
            latest_progress = max(progress_list, key=lambda x: x["last_read_at"])
            
            # 简单估算总阅读时间（基于进度百分比，每部小说假设10小时）
            total_reading_time_minutes = int(sum(p["progress_percentage"] for p in progress_list) * 6)  # 6分钟/百分比
            
            stats = ReadingStats(
                total_novels=total_novels,
                novels_in_progress=novels_in_progress,
                novels_completed=novels_completed,
                total_reading_time_minutes=total_reading_time_minutes,
                average_progress=round(average_progress, 2),
                last_read_novel_id=latest_progress["novel_id"],
                last_read_at=latest_progress["last_read_at"]
            )
            
            logger.info("Calculated user reading stats", 
                       user_id=user_id, total_novels=total_novels, 
                       average_progress=stats.average_progress)
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user reading stats: {e}", user_id=user_id)
            raise


# 创建单例实例
novel_service = NovelService()
