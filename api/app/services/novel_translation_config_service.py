"""
小说用户翻译配置服务类
处理用户对每本小说的个性化翻译和阅读设置
"""

from typing import List, Optional, Dict, Any
from app.services.supabase_client import supabase_service
from app.schemas.novel_translation_config_schemas import (
    NovelTranslationConfigCreate, NovelTranslationConfigUpdate, 
    NovelTranslationConfigResponse
)
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class NovelTranslationConfigService:
    """小说翻译配置服务类"""
    
    def __init__(self):
        # 使用service role客户端
        self.service_client = supabase_service.get_client()
    
    def _get_user_client(self, access_token: str):
        """获取用户客户端（遵循RLS策略）"""
        if not access_token:
            raise ValueError("此操作需要用户访问令牌。")
        return supabase_service.get_user_client(access_token)
    
    # ================================
    # 翻译配置 CRUD 操作
    # ================================
    
    async def create_or_update_config(
        self, 
        user_id: uuid.UUID, 
        config_data: NovelTranslationConfigCreate, 
        access_token: str
    ) -> NovelTranslationConfigResponse:
        """创建或更新翻译配置（使用 UPSERT 操作）"""
        try:
            # 验证和转换UUID
            try:
                # 确保novel_id是有效的UUID格式
                novel_uuid = str(uuid.UUID(config_data.novel_id))
                user_uuid = str(user_id)
            except ValueError as ve:
                logger.error(f"Invalid UUID format - novel_id: {config_data.novel_id}, user_id: {user_id}")
                raise Exception(f"无效的UUID格式: {str(ve)}")
            
            # 准备数据
            data = {
                "user_id": user_uuid,
                "novel_id": novel_uuid,
                "is_translation_enabled": config_data.is_translation_enabled,
                "source_language": config_data.source_language,
                "target_language": config_data.target_language,
                "custom_source_language": config_data.custom_source_language,
                "custom_target_language": config_data.custom_target_language,
                "translation_mode": config_data.translation_mode,
                "mixed_ratio": config_data.mixed_ratio,
                "mixed_seed": config_data.mixed_seed,
                "font_size": config_data.font_size,
                "font_family": config_data.font_family,
                "is_ai_visible": config_data.is_ai_visible,
                "last_used_at": datetime.utcnow().isoformat()
            }
            
            # logger.info(f"Attempting to create/update config with data: {data}")
            
            # 使用用户客户端确保RLS策略生效
            client = self._get_user_client(access_token)
            
            # 使用 UPSERT 操作：如果存在就更新，不存在就创建
            response = client.table("novel_user_translation_config").upsert(
                data, 
                on_conflict="user_id,novel_id"  # 基于用户ID和小说ID的唯一约束
            ).execute()
            
            logger.info(f"Supabase response: {response}")
            
            if response.data and len(response.data) > 0:
                config_dict = response.data[0]
                logger.info(f"Translation config created/updated successfully: config_id={config_dict['id']}, user_id={user_id}, novel_id={config_data.novel_id}")
                return NovelTranslationConfigResponse(**config_dict)
            else:
                error_msg = f"Failed to create/update translation config - no data returned. Response: {response}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            error_detail = f"Error creating/updating translation config: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            raise Exception(f"创建/更新翻译配置失败: {error_detail}")
    
    async def get_config(
        self, 
        user_id: uuid.UUID, 
        novel_id: str, 
        access_token: str
    ) -> Optional[NovelTranslationConfigResponse]:
        """获取用户对特定小说的翻译配置"""
        try:
            # 验证UUID格式
            try:
                novel_uuid = str(uuid.UUID(novel_id))
                user_uuid = str(user_id)
            except ValueError as ve:
                logger.error(f"Invalid UUID format - novel_id: {novel_id}, user_id: {user_id}")
                raise Exception(f"无效的UUID格式: {str(ve)}")
            
            client = self._get_user_client(access_token)
            
            response = client.table("novel_user_translation_config").select("*").eq(
                "user_id", user_uuid
            ).eq(
                "novel_id", novel_uuid
            ).execute()
            
            if response.data and len(response.data) > 0:
                config_dict = response.data[0]
                logger.info(f"Translation config retrieved successfully: config_id={config_dict['id']}")
                return NovelTranslationConfigResponse(**config_dict)
            else:
                logger.warning(f"No translation config found for user {user_id} and novel {novel_id}")
                return None
                
        except Exception as e:
            error_detail = f"获取翻译配置失败: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            raise Exception(error_detail)
    
    async def update_config(
        self, 
        user_id: uuid.UUID, 
        novel_id: str, 
        config_update: NovelTranslationConfigUpdate, 
        access_token: str
    ) -> Optional[NovelTranslationConfigResponse]:
        """更新翻译配置"""
        try:
            # 验证UUID格式
            try:
                novel_uuid = str(uuid.UUID(novel_id))
                user_uuid = str(user_id)
            except ValueError as ve:
                logger.error(f"Invalid UUID format - novel_id: {novel_id}, user_id: {user_id}")
                raise Exception(f"无效的UUID格式: {str(ve)}")
            
            # 只更新提供的字段
            update_data = {}
            if config_update.is_translation_enabled is not None:
                update_data["is_translation_enabled"] = config_update.is_translation_enabled
            if config_update.source_language is not None:
                update_data["source_language"] = config_update.source_language
            if config_update.target_language is not None:
                update_data["target_language"] = config_update.target_language
            if config_update.custom_source_language is not None:
                update_data["custom_source_language"] = config_update.custom_source_language
            if config_update.custom_target_language is not None:
                update_data["custom_target_language"] = config_update.custom_target_language
            if config_update.translation_mode is not None:
                update_data["translation_mode"] = config_update.translation_mode
            if config_update.mixed_ratio is not None:
                update_data["mixed_ratio"] = config_update.mixed_ratio
            if config_update.mixed_seed is not None:
                update_data["mixed_seed"] = config_update.mixed_seed
            if config_update.font_size is not None:
                update_data["font_size"] = config_update.font_size
            if config_update.font_family is not None:
                update_data["font_family"] = config_update.font_family
            if config_update.is_ai_visible is not None:
                update_data["is_ai_visible"] = config_update.is_ai_visible
            
            if not update_data:
                raise ValueError("No fields to update")
            
            # 添加更新时间
            update_data["last_used_at"] = datetime.utcnow().isoformat()
            
            client = self._get_user_client(access_token)
            
            response = client.table("novel_user_translation_config").update(
                update_data
            ).eq(
                "user_id", user_uuid
            ).eq(
                "novel_id", novel_uuid
            ).execute()
            
            if response.data and len(response.data) > 0:
                config_dict = response.data[0]
                logger.info(f"Translation config updated successfully: config_id={config_dict['id']}, user_id={user_id}, novel_id={novel_id}")
                return NovelTranslationConfigResponse(**config_dict)
            else:
                logger.warning(f"No translation config found to update for user {user_id} and novel {novel_id}")
                return None
                
        except Exception as e:
            error_detail = f"更新翻译配置失败: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            raise Exception(error_detail)
    
    async def delete_config(
        self, 
        user_id: uuid.UUID, 
        novel_id: str, 
        access_token: str
    ) -> bool:
        """删除翻译配置"""
        try:
            # 验证UUID格式
            try:
                novel_uuid = str(uuid.UUID(novel_id))
                user_uuid = str(user_id)
            except ValueError as ve:
                logger.error(f"Invalid UUID format - novel_id: {novel_id}, user_id: {user_id}")
                raise Exception(f"无效的UUID格式: {str(ve)}")
            
            client = self._get_user_client(access_token)
            
            response = client.table("novel_user_translation_config").delete().eq(
                "user_id", user_uuid
            ).eq(
                "novel_id", novel_uuid
            ).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(
                    "Translation config deleted successfully", 
                    user_id=user_id,
                    novel_id=novel_id
                )
                return True
            else:
                logger.warning(f"No translation config found to delete for user {user_id} and novel {novel_id}")
                return False
                
        except Exception as e:
            error_detail = f"删除翻译配置失败: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            raise Exception(error_detail)
    
    async def get_user_configs(
        self, 
        user_id: uuid.UUID, 
        access_token: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[NovelTranslationConfigResponse]:
        """获取用户的所有翻译配置"""
        try:
            user_uuid = str(user_id)
            client = self._get_user_client(access_token)
            
            response = client.table("novel_user_translation_config").select("*").eq(
                "user_id", user_uuid
            ).order(
                "last_used_at", desc=True
            ).range(offset, offset + limit - 1).execute()
            
            configs = []
            if response.data:
                for config_dict in response.data:
                    configs.append(NovelTranslationConfigResponse(**config_dict))
            
            logger.info(f"Retrieved {len(configs)} translation configs for user {user_id}")
            return configs
            
        except Exception as e:
            error_detail = f"获取用户翻译配置失败: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            raise Exception(error_detail)
    
    async def get_batch_configs(
        self, 
        user_id: uuid.UUID, 
        novel_ids: List[str], 
        access_token: str
    ) -> Dict[str, Optional[NovelTranslationConfigResponse]]:
        """批量获取用户对多本小说的翻译配置"""
        try:
            # 验证UUID格式
            user_uuid = str(user_id)
            validated_novel_ids = []
            for novel_id in novel_ids:
                try:
                    validated_novel_ids.append(str(uuid.UUID(novel_id)))
                except ValueError:
                    logger.warning(f"Invalid novel_id UUID format: {novel_id}")
                    # 跳过无效的UUID，继续处理其他的
                    continue
            
            client = self._get_user_client(access_token)
            
            response = client.table("novel_user_translation_config").select("*").eq(
                "user_id", user_uuid
            ).in_(
                "novel_id", validated_novel_ids
            ).execute()
            
            # 构建结果字典
            result = {}
            config_map = {}
            
            if response.data:
                for config_dict in response.data:
                    config = NovelTranslationConfigResponse(**config_dict)
                    config_map[config.novel_id] = config
            
            # 确保所有请求的novel_id都在结果中（没有配置的设为None）
            for novel_id in novel_ids:
                result[novel_id] = config_map.get(novel_id)
            
            logger.info(f"Retrieved batch translation configs for {len(novel_ids)} novels, {len(config_map)} found")
            return result
            
        except Exception as e:
            error_detail = f"批量获取翻译配置失败: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            raise Exception(error_detail)
    
    async def update_last_used(
        self, 
        user_id: uuid.UUID, 
        novel_id: str, 
        access_token: str
    ) -> bool:
        """更新配置的最后使用时间"""
        try:
            # 验证UUID格式
            try:
                novel_uuid = str(uuid.UUID(novel_id))
                user_uuid = str(user_id)
            except ValueError as ve:
                logger.error(f"Invalid UUID format - novel_id: {novel_id}, user_id: {user_id}")
                return False
            
            client = self._get_user_client(access_token)
            
            response = client.table("novel_user_translation_config").update({
                "last_used_at": datetime.utcnow().isoformat()
            }).eq(
                "user_id", user_uuid
            ).eq(
                "novel_id", novel_uuid
            ).execute()
            
            return response.data and len(response.data) > 0
            
        except Exception as e:
            error_detail = f"更新最后使用时间失败: {type(e).__name__}: {str(e)}"
            logger.error(error_detail)
            return False