from typing import List, Optional, Dict, Any, Tuple
from app.services.supabase_client import supabase_service
from app.schemas.material_schemas import (
    MaterialLibraryCreate, MaterialLibraryUpdate, MaterialLibraryResponse,
    MaterialArticleCreate, MaterialArticleUpdate, MaterialArticleResponse,
    MaterialSegmentCreate, MaterialSegmentUpdate, MaterialSegmentResponse,
    MaterialCollectionCreate, MaterialCollectionUpdate, MaterialCollectionResponse,
    MaterialLibraryQuery, MaterialArticleQuery, MaterialSegmentBatchCreate,
    MaterialCollectionArticleAdd
)
import structlog
from datetime import datetime
from uuid import UUID
import json

logger = structlog.get_logger()


class MaterialService:
    """文章阅读材料服务"""
    
    def __init__(self):
        self.service_client = supabase_service.get_client()  # Service role客户端
    
    # 文章库相关方法
    async def create_library(self, user_id: str, library_data: MaterialLibraryCreate) -> MaterialLibraryResponse:
        """创建文章库"""
        try:
            data = {
                "name": library_data.name,
                "description": library_data.description,
                "user_id": user_id,
                "library_type": library_data.library_type,
                "target_language": library_data.target_language,
                "explanation_language": library_data.explanation_language,
                "is_public": library_data.is_public
            }
            
            response = self.service_client.table("material_libraries").insert(data).execute()
            
            if response.data and len(response.data) > 0:
                library_dict = response.data[0]
                return MaterialLibraryResponse(**library_dict)
            else:
                raise Exception("Failed to create library")
                
        except Exception as e:
            logger.error(f"Error creating library: {e}")
            raise
    
    async def get_library(self, user_id: str, library_id: str) -> Optional[MaterialLibraryResponse]:
        """获取单个文章库"""
        try:
            response = self.service_client.table("material_libraries").select("*").eq("id", library_id).execute()
            
            if response.data and len(response.data) > 0:
                library_dict = response.data[0]
                # 检查权限
                if library_dict["user_id"] != user_id and not library_dict["is_public"]:
                    return None
                return MaterialLibraryResponse(**library_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error getting library: {e}")
            raise
    
    async def list_libraries(self, user_id: str, query: MaterialLibraryQuery) -> Tuple[List[MaterialLibraryResponse], int]:
        """获取文章库列表"""
        try:
            # 构建查询
            query_builder = self.service_client.table("material_libraries").select("*", count="exact")
            
            # 权限过滤：只能看到自己的或公开的
            query_builder = query_builder.or_(f"user_id.eq.{user_id},is_public.eq.true")
            
            # 其他过滤条件
            if query.library_type:
                query_builder = query_builder.eq("library_type", query.library_type)
            if query.is_public is not None:
                query_builder = query_builder.eq("is_public", query.is_public)
            if query.search:
                query_builder = query_builder.ilike("name", f"%{query.search}%")
            
            # 分页
            offset = (query.page - 1) * query.page_size
            query_builder = query_builder.range(offset, offset + query.page_size - 1)
            
            # 排序
            query_builder = query_builder.order("created_at", desc=True)
            
            response = query_builder.execute()
            
            libraries = [MaterialLibraryResponse(**item) for item in response.data]
            total = response.count or 0
            
            return libraries, total
            
        except Exception as e:
            logger.error(f"Error listing libraries: {e}")
            raise
    
    async def update_library(self, user_id: str, library_id: str, library_data: MaterialLibraryUpdate) -> Optional[MaterialLibraryResponse]:
        """更新文章库"""
        try:
            # 先检查权限
            library = await self.get_library(user_id, library_id)
            if not library or library.user_id != user_id:
                return None
            
            # 准备更新数据
            update_data = {}
            if library_data.name is not None:
                update_data["name"] = library_data.name
            if library_data.description is not None:
                update_data["description"] = library_data.description
            if library_data.library_type is not None:
                update_data["library_type"] = library_data.library_type
            if library_data.target_language is not None:
                update_data["target_language"] = library_data.target_language
            if library_data.explanation_language is not None:
                update_data["explanation_language"] = library_data.explanation_language
            if library_data.is_public is not None:
                update_data["is_public"] = library_data.is_public
            
            if not update_data:
                return library
            
            response = self.service_client.table("material_libraries").update(update_data).eq("id", library_id).execute()
            
            if response.data and len(response.data) > 0:
                return MaterialLibraryResponse(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error updating library: {e}")
            raise
    
    async def delete_library(self, user_id: str, library_id: str) -> bool:
        """删除文章库（软删除）"""
        try:
            # 先检查权限
            library = await self.get_library(user_id, library_id)
            if not library or library.user_id != user_id:
                return False
            
            response = self.service_client.table("material_libraries").update({"is_deleted": True}).eq("id", library_id).execute()
            
            return response.data and len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting library: {e}")
            raise
    
    # 文章相关方法
    async def create_article(self, user_id: str, article_data: MaterialArticleCreate, access_token: str) -> MaterialArticleResponse:
        """创建文章 - 使用RLS策略"""
        try:
            user_client = supabase_service.get_user_client(access_token)
            
            data = {
                "title": article_data.title,
                "content": article_data.content,
                "file_type": article_data.file_type,
                "user_id": user_id,
                "library_id": article_data.library_id,
                "target_language": article_data.target_language,
                "category": article_data.category,
                "tags": article_data.tags,
                "is_public": article_data.is_public,
                "description": article_data.description
            }

            # 使用用户客户端，遵循RLS策略
            response = user_client.table("material_articles").insert(data).execute()
            
            if response.data and len(response.data) > 0:
                article_dict = response.data[0]
                return MaterialArticleResponse(**article_dict)
            else:
                logger.error("Failed to create article, response data is empty.", response=response)
                raise Exception("Failed to create article")
                
        except Exception as e:
            logger.error(f"Error creating article with RLS: {e}")
            raise
    
    async def get_article(self, user_id: str, article_id: str, access_token: str = None) -> Optional[MaterialArticleResponse]:
        """获取单个文章 - 使用RLS策略"""
        try:
            # 使用用户客户端，遵循RLS策略
            if access_token:
                user_client = supabase_service.get_user_client(access_token)
                response = user_client.table("material_articles").select("*").eq("id", article_id).execute()
            else:
                # 回退到service client但进行手动权限检查
                response = self.service_client.table("material_articles").select("*").eq("id", article_id).execute()
            
            if response.data and len(response.data) > 0:
                article_dict = response.data[0]
                
                # 如果没有使用access_token，需要手动检查权限
                if not access_token:
                    if article_dict["user_id"] != user_id and not article_dict["is_public"]:
                        logger.warning(f"Access denied to article {article_id} for user {user_id}")
                        return None
                
                return MaterialArticleResponse(**article_dict)
            return None
            
        except Exception as e:
            logger.error(f"Error getting article {article_id} for user {user_id}: {e}")
            # 在生产环境中，RLS错误可能表现为查询失败
            return None
    
    async def list_articles(self, user_id: str, query: MaterialArticleQuery, access_token: str) -> Tuple[List[MaterialArticleResponse], int]:
        """获取文章列表（使用优化视图和RLS）"""
        try:
            user_client = supabase_service.get_user_client(access_token)
            query_builder = user_client.table("article_stats_view").select("*", count="exact")
            
            # 显式添加用户过滤条件，确保只返回当前用户的文章或公开文章
            query_builder = query_builder.or_(f"user_id.eq.{user_id},is_public.eq.true")
            
            # 添加其他过滤条件
            if query.library_id:
                query_builder = query_builder.eq("library_id", query.library_id)
            if query.status:
                query_builder = query_builder.eq("status", query.status)
            if query.is_public is not None:
                query_builder = query_builder.eq("is_public", query.is_public)
            if query.difficulty_level:
                query_builder = query_builder.eq("difficulty_level", query.difficulty_level)
            if query.category:
                query_builder = query_builder.eq("category", query.category)
            if query.search:
                query_builder = query_builder.or_(f"title.ilike.%{query.search}%,content.ilike.%{query.search}%")
            
            offset = (query.page - 1) * query.page_size
            query_builder = query_builder.range(offset, offset + query.page_size - 1)
            query_builder = query_builder.order("created_at", desc=True)
            
            response = query_builder.execute()
            
            articles = [MaterialArticleResponse(**item) for item in response.data]
            total = response.count or 0
            
            return articles, total
            
        except Exception as e:
            logger.error(f"Error listing articles with RLS: {e}")
            raise
    
    async def update_article(self, user_id: str, article_id: str, article_data: MaterialArticleUpdate, access_token: str) -> Optional[MaterialArticleResponse]:
        """更新文章 - 使用RLS策略"""
        try:
            user_client = supabase_service.get_user_client(access_token)
            
            # RLS会确保只有所有者才能更新
            update_data = {}
            for field, value in article_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    update_data[field] = value
            
            if not update_data:
                return await self.get_article(user_id, article_id, access_token)

            response = user_client.table("material_articles").update(update_data).eq("id", article_id).execute()
            
            if response.data and len(response.data) > 0:
                return MaterialArticleResponse(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error updating article with RLS: {e}")
            raise
    
    async def delete_article(self, user_id: str, article_id: str, access_token: str) -> bool:
        """删除文章及其所有相关数据 - 使用RLS策略"""
        try:
            user_client = supabase_service.get_user_client(access_token)
            
            # 首先删除所有相关的分段
            await self._delete_article_segments(article_id, access_token)
            
            # 然后删除文章本身，RLS会确保权限
            response = user_client.table("material_articles").delete().eq("id", article_id).execute()
            
            article_deleted = response.data and len(response.data) > 0
            logger.info(f"Deleted article {article_id} via RLS: {article_deleted}")
            
            return article_deleted
            
        except Exception as e:
            logger.error(f"Error deleting article with RLS: {e}")
            raise
    
    # 文章分段相关方法
    async def create_segment(self, user_id: str, segment_data: MaterialSegmentCreate, access_token: str) -> MaterialSegmentResponse:
        """创建文章分段 - 使用RLS策略"""
        try:
            # RLS会处理文章权限检查
            user_client = supabase_service.get_user_client(access_token)
            
            data = {
                "article_id": segment_data.article_id,
                "original_text": segment_data.original_text,
                "translation": segment_data.translation,
                "reading_text": segment_data.reading_text,
                "is_new_paragraph": segment_data.is_new_paragraph,
                "segment_order": segment_data.segment_order,
                "grammar_items": [item.model_dump() for item in segment_data.grammar_items],
                "vocabulary_items": [item.model_dump() for item in segment_data.vocabulary_items]
            }
            
            response = user_client.table("material_segments").insert(data).execute()
            
            if response.data and len(response.data) > 0:
                segment_dict = response.data[0]
                return MaterialSegmentResponse(**segment_dict)
            else:
                raise Exception("Failed to create segment with RLS")
                
        except Exception as e:
            logger.error(f"Error creating segment with RLS: {e}")
            raise
    
    async def create_segments_batch(self, user_id: str, batch_data: MaterialSegmentBatchCreate, access_token: str) -> List[MaterialSegmentResponse]:
        """批量创建文章分段 - 使用RLS策略"""
        try:
            # RLS会处理文章权限检查
            user_client = supabase_service.get_user_client(access_token)
            
            segments_data = []
            for segment in batch_data.segments:
                data = {
                    "article_id": batch_data.article_id,
                    "original_text": segment.original_text,
                    "translation": segment.translation,
                    "reading_text": segment.reading_text,
                    "is_new_paragraph": segment.is_new_paragraph,
                    "segment_order": segment.segment_order,
                    "grammar_items": [item.model_dump() for item in segment.grammar_items],
                    "vocabulary_items": [item.model_dump() for item in segment.vocabulary_items]
                }
                segments_data.append(data)
            
            response = user_client.table("material_segments").insert(segments_data).execute()
            
            if response.data:
                return [MaterialSegmentResponse(**item) for item in response.data]
            else:
                raise Exception("Failed to create segments batch with RLS")
                
        except Exception as e:
            logger.error(f"Error creating segments batch with RLS: {e}")
            raise
    
    async def get_article_segments(self, user_id: str, article_id: str, page: int = 1, page_size: int = 100, access_token: str = None) -> Tuple[List[MaterialSegmentResponse], int]:
        """获取文章的分段列表 - 使用RLS策略"""
        try:
            # Primary path: Use user_client with access_token for RLS-compliant queries
            if access_token:
                try:
                    user_client = supabase_service.get_user_client(access_token)
                    query_builder = user_client.table("material_segments").select("*", count="exact").eq("article_id", article_id)
                    
                    offset = (page - 1) * page_size
                    query_builder = query_builder.range(offset, offset + page_size - 1)
                    query_builder = query_builder.order("segment_order", desc=False)
                    
                    response = query_builder.execute()
                    
                    segments = [MaterialSegmentResponse(**item) for item in response.data]
                    total = response.count or 0
                    
                    return segments, total
                    
                except Exception as e:
                    # Check if this is an RLS permission error
                    error_str = str(e).lower()
                    if "rls" in error_str or "permission" in error_str or "policy" in error_str:
                        logger.warning(f"RLS permission denied for user {user_id} accessing article {article_id} segments: {e}")
                        return [], 0
                    else:
                        # Re-raise non-RLS errors
                        raise
            else:
                # Fallback path: Use service_client with manual permission validation
                logger.info(f"Using service_client fallback for article {article_id} segments (no access_token)")
                
                # First, manually validate article permissions
                article = await self.get_article(user_id, article_id, access_token)
                if not article:
                    logger.warning(f"Article {article_id} not found or no permission for user {user_id}")
                    return [], 0
                
                # Use service_client for segments query since we've validated article access
                query_builder = self.service_client.table("material_segments").select("*", count="exact").eq("article_id", article_id)
                
                offset = (page - 1) * page_size
                query_builder = query_builder.range(offset, offset + page_size - 1)
                query_builder = query_builder.order("segment_order", desc=False)
                
                response = query_builder.execute()
                
                segments = [MaterialSegmentResponse(**item) for item in response.data]
                total = response.count or 0
                
                return segments, total
            
        except Exception as e:
            logger.error(f"Error getting article segments: {e}", extra={
                "user_id": user_id,
                "article_id": article_id,
                "has_access_token": access_token is not None,
                "error_type": type(e).__name__
            })
            # Distinguish between RLS failures and other errors
            error_str = str(e).lower()
            if "rls" in error_str or "permission" in error_str or "policy" in error_str:
                # RLS permission error - return empty result instead of raising
                logger.warning(f"RLS policy prevented access to segments for article {article_id}, user {user_id}")
                return [], 0
            else:
                # Other errors should be raised
                raise
    
    async def update_segment(self, user_id: str, segment_id: str, segment_data: MaterialSegmentUpdate, access_token: str) -> Optional[MaterialSegmentResponse]:
        """更新文章分段 - 使用RLS策略"""
        try:
            user_client = supabase_service.get_user_client(access_token)

            # RLS会确保权限
            update_data = {}
            for field, value in segment_data.model_dump(exclude_unset=True).items():
                if value is not None:
                    if field in ["grammar_items", "vocabulary_items"] and isinstance(value, list):
                        update_data[field] = [item.model_dump() if hasattr(item, 'model_dump') else item for item in value]
                    else:
                        update_data[field] = value
            
            if not update_data:
                segment_response = user_client.table("material_segments").select("*").eq("id", segment_id).execute()
                if segment_response.data:
                    return MaterialSegmentResponse(**segment_response.data[0])
                return None
            
            response = user_client.table("material_segments").update(update_data).eq("id", segment_id).execute()
            
            if response.data and len(response.data) > 0:
                return MaterialSegmentResponse(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error updating segment with RLS: {e}")
            raise
    
    async def delete_segment(self, user_id: str, segment_id: str, access_token: str) -> bool:
        """删除分段 - 使用RLS策略"""
        try:
            user_client = supabase_service.get_user_client(access_token)
            
            # RLS会确保权限
            response = user_client.table("material_segments").delete().eq("id", segment_id).execute()
            
            return response.data and len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error deleting segment with RLS: {e}")
            return False

    async def auto_segment_article_by_paragraph(self, user_id: str, article_id: str, access_token: str) -> List[MaterialSegmentResponse]:
        """
        自动将文章按段落分段 - 使用RLS策略
        实现逻辑：
        - 按句号(。.)和换行符(\n)分段
        - 换行后的段落标记为新段落
        - 句号分割的段落标记为false（非新段落）
        """
        try:
            # 获取文章内容 - 使用RLS
            article = await self.get_article(user_id, article_id, access_token)
            if not article:
                raise Exception("Article not found or no permission")
            
            # 先删除该文章的所有现有分段
            await self._delete_article_segments(article_id, access_token)
            
            content = article.content
            processed_segments = []
            is_new_paragraph_flags = []
            
            # 首先按换行符分割
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # 跳过空行
                if not line:
                    continue
                
                # 如果是短文本（可能是标题）或不包含句号的文本，直接作为独立段落
                if len(line) <= 20 or not any(char in line for char in '。.'):
                    processed_segments.append(line)
                    is_new_paragraph_flags.append(True)  # 换行后的段落标记为新段落
                    continue
                
                # 处理包含句号的长段落
                import re
                segments = re.split(r'([。.])', line)
                is_first_segment = True  # 标记是否是该行的第一个段落
                
                for i in range(0, len(segments)-1, 2):
                    if segments[i].strip():
                        current_segment = segments[i] + (segments[i+1] if i+1 < len(segments) else '')
                        processed_segments.append(current_segment)
                        # 只有行的第一个段落（换行后）标记为新段落，句号分割的段落标记为false
                        is_new_paragraph_flags.append(is_first_segment)
                        is_first_segment = False
                
                # 处理最后一个没有句号的部分
                if segments[-1].strip() and not re.match(r'[。.]', segments[-1]):
                    processed_segments.append(segments[-1])
                    is_new_paragraph_flags.append(is_first_segment)
            
            # 限制段落数量
            MAX_SEGMENTS = 400
            if len(processed_segments) > MAX_SEGMENTS:
                processed_segments = processed_segments[:MAX_SEGMENTS]
                is_new_paragraph_flags = is_new_paragraph_flags[:MAX_SEGMENTS]
            
            # 创建分段数据
            segments_data = []
            for i, (segment_text, is_new_paragraph) in enumerate(zip(processed_segments, is_new_paragraph_flags)):
                if segment_text:
                    segments_data.append({
                        "original_text": segment_text,
                        "translation": "",
                        "reading_text": "",
                        "is_new_paragraph": is_new_paragraph,
                        "segment_order": i,
                        "grammar_items": [],
                        "vocabulary_items": []
                    })
            
            # 批量创建分段
            if segments_data:
                batch_data = MaterialSegmentBatchCreate(
                    article_id=article_id,
                    segments=[MaterialSegmentCreate(article_id=article_id, **data) for data in segments_data]
                )
                
                segments = await self.create_segments_batch(user_id, batch_data, access_token)
                return segments
            
            return []
            
        except Exception as e:
            logger.error(f"Error auto-segmenting article by paragraph: {e}")
            raise

    async def _delete_article_segments(self, article_id: str, access_token: str) -> bool:
        """删除文章的所有分段 - 使用RLS策略"""
        try:
            user_client = supabase_service.get_user_client(access_token)
            response = user_client.table("material_segments").delete().eq("article_id", article_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting article segments with RLS: {e}")
            return False

    # ================================
    # 统计信息
    # ================================
    
    async def get_user_articles_stats(self, user_id: str, access_token: str = None) -> Dict[str, Any]:
        """获取用户文章统计信息"""
        try:
            if access_token:
                user_client = supabase_service.get_user_client(access_token)
                # 查询用户的文章
                response = user_client.table("material_articles")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
            else:
                # 使用服务客户端进行查询
                response = self.service_client.table("material_articles")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .execute()
            
            articles = response.data or []
            
            # 计算统计信息
            total_articles = len(articles)
            public_articles = sum(1 for article in articles if article.get("is_public", False))
            private_articles = total_articles - public_articles
            
            # 按状态分组统计
            by_status = {}
            for article in articles:
                status = article.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1
            
            # 按难度分组统计
            by_difficulty = {}
            for article in articles:
                difficulty = article.get("difficulty_level", "unknown")
                by_difficulty[difficulty] = by_difficulty.get(difficulty, 0) + 1
            
            # 按分类分组统计
            by_category = {}
            for article in articles:
                category = article.get("category", "unknown")
                by_category[category] = by_category.get(category, 0) + 1
            
            return {
                "total_articles": total_articles,
                "public_articles": public_articles,
                "private_articles": private_articles,
                "by_status": by_status,
                "by_difficulty": by_difficulty,
                "by_category": by_category
            }
            
        except Exception as e:
            logger.error(f"Error getting user articles stats: {e}", user_id=user_id)
            raise


# 创建全局材料服务实例
material_service = MaterialService() 