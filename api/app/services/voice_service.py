import requests
import logging
import uuid
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime
from app.core.config import settings
from app.core.logging_config import LoggingConfig
from app.schemas.points import ServiceType, TransactionType

logger = LoggingConfig.get_logger_for_service("voice_service")


class VoiceService:
    """语音服务，使用Minimax API进行文本转语音"""
    
    # 支持的语言增强选项
    SUPPORTED_LANGUAGE_BOOST = {
        'Chinese', 'Chinese,Yue', 'English', 'Arabic', 'Russian', 'Spanish', 
        'French', 'Portuguese', 'German', 'Turkish', 'Dutch', 'Ukrainian', 
        'Vietnamese', 'Indonesian', 'Japanese', 'Italian', 'Korean', 'Thai', 
        'Polish', 'Romanian', 'Greek', 'Czech', 'Finnish', 'Hindi', 'auto'
    }

    DEFAULT_VOICE_ID = "male-qn-qingse"

    SUPPORTED_VOICES: Dict[str, Dict[str, str]] = {
        "male-qn-qingse": {"name": "青涩青年音色", "language": "zh-CN", "gender": "male"},
        "male-qn-jingying": {"name": "精英青年音色", "language": "zh-CN", "gender": "male"},
        "female-shaonv": {"name": "少女音色", "language": "zh-CN", "gender": "female"},
        "female-yujie": {"name": "御姐音色", "language": "zh-CN", "gender": "female"},
        "presenter_male": {"name": "播报男声", "language": "zh-CN", "gender": "male"},
        "presenter_female": {"name": "新闻女声", "language": "zh-CN", "gender": "female"},
        "Chinese (Mandarin)_Gentleman": {"name": "温润男声", "language": "zh-CN", "gender": "male"},
        "Chinese (Mandarin)_Warm_Girl": {"name": "温暖少女", "language": "zh-CN", "gender": "female"},
        "female-en-suri": {"name": "Suri", "language": "en-US", "gender": "female"},
        "English_Graceful_Lady": {"name": "Graceful Lady", "language": "en-US", "gender": "female"},
        "English_Trustworthy_Man": {"name": "Trustworthy Man", "language": "en-US", "gender": "male"},
        "Japanese_GentleButler": {"name": "Gentle Butler", "language": "ja-JP", "gender": "male"},
        "Japanese_GracefulMaiden": {"name": "Graceful Maiden", "language": "ja-JP", "gender": "female"},
        "Japanese_DominantMan": {"name": "Dominant Man", "language": "ja-JP", "gender": "male"},
    }

    VOICE_CATEGORY_MAP: Dict[str, List[str]] = {
        "chinese_voices": [
            "male-qn-qingse",
            "male-qn-jingying",
            "female-shaonv",
            "female-yujie",
            "presenter_male",
            "presenter_female",
            "Chinese (Mandarin)_Gentleman",
            "Chinese (Mandarin)_Warm_Girl",
        ],
        "english_voices": [
            "female-en-suri",
            "English_Graceful_Lady",
            "English_Trustworthy_Man",
        ],
        "japanese_voices": [
            "Japanese_GentleButler",
            "Japanese_GracefulMaiden",
            "Japanese_DominantMan",
        ],
    }

    VOICE_ALIASES: Dict[str, str] = {
        "female-jp-aki": "Japanese_GracefulMaiden",
        "female_jp_aki": "Japanese_GracefulMaiden",
        "japanese_gentlebutler": "Japanese_GentleButler",
        "female-en-suri": "English_Graceful_Lady",
        "female_en_suri": "English_Graceful_Lady",
    }
    
    def __init__(self):
        self.base_url = "https://api.minimaxi.com/v1/t2a_v2"
        self.api_key = settings.minimax_api_key
        self.group_id = settings.minimax_groupid
        
        if not self.api_key or not self.group_id:
            logger.warning("Minimax API配置不完整，语音功能可能无法正常工作")
    
    def calculate_voice_points(self, text: str) -> int:
        """
        根据文本长度计算所需积分
        
        Args:
            text: 要转换的文本
            
        Returns:
            所需积分数量
        """
        text_length = len(text)
        
        if text_length <= 5:
            return 2
        elif text_length <= 50:
            return 4
        elif text_length <= 100:
            return 8
        else:
            # 100个字以上每100字扣10积分
            additional_hundreds = (text_length - 100 + 99) // 100  # 向上取整
            return 8 + (additional_hundreds * 10)
    
    async def text_to_speech(
        self,
        text: str,
        user_id: str,
        voice_id: str = "male-qn-qingse",
        speed: float = 1.0,
        pitch: float = 0,
        volume: float = 1.0,
        sample_rate: int = 32000,
        bitrate: int = 128000,
        audio_format: str = "mp3",
        auto_charge: bool = True,
        access_token: str = None,
        language_boost: Optional[str] = "auto"
    ) -> Dict[str, Any]:
        """
        将文本转换为语音（包含积分扣除）
        
        Args:
            text: 要转换的文本
            user_id: 用户ID
            voice_id: 声音ID
            speed: 语速 (0.1-2.0)
            pitch: 音调 (-1.0-1.0)
            volume: 音量 (0.1-2.0)
            sample_rate: 采样率
            bitrate: 比特率
            audio_format: 音频格式
            auto_charge: 是否自动扣费
            access_token: 访问令牌
            language_boost: 语言增强选项，支持指定小语种和方言的识别能力，默认为"auto"
            
        Returns:
            包含成功状态、音频数据和积分信息的字典
        """
        if not self.api_key or not self.group_id:
            logger.error("Minimax API配置缺失")
            return {
                "success": False,
                "error": "api_config_missing",
                "message": "Minimax API配置缺失"
            }
        
        # 验证language_boost参数
        if language_boost and language_boost not in self.SUPPORTED_LANGUAGE_BOOST:
            logger.warning(f"不支持的language_boost值: {language_boost}, 使用默认值 'auto'")
            language_boost = "auto"

        resolved_voice_id, alias_applied, fallback_applied = self._resolve_voice_id(voice_id)
        if alias_applied:
            logger.warning(f"语音ID {voice_id} 使用兼容别名，映射为 {resolved_voice_id}")
        elif fallback_applied and voice_id:
            logger.warning(f"不支持的语音ID: {voice_id}，已回退到默认声音 {resolved_voice_id}")
        voice_id = resolved_voice_id
        
        # 1. 计算所需积分
        points_needed = self.calculate_voice_points(text)
        if LoggingConfig.should_log_debug():
            logger.debug(f"语音合成积分计算 - 文本长度: {len(text)}, 所需积分: {points_needed}")
        
        # 2. 积分检查和扣除
        points_transaction = None
        user_points_service = None
        if auto_charge and points_needed > 0:
            try:
                # 创建带用户token的points_service实例
                from app.services.points_service import PointsService
                user_points_service = PointsService(access_token=access_token)
                
                # 获取用户当前积分
                balance = await user_points_service.get_user_balance(user_id)
                if not balance:
                    logger.error(f"无法获取用户 {user_id} 的积分余额")
                    return {
                        "success": False,
                        "error": "balance_check_failed",
                        "message": "无法获取用户积分余额"
                    }
                
                current_points = balance.total_points
                if current_points < points_needed:
                    logger.warning(f"积分不足 - 用户: {user_id}, 当前: {current_points}, 需要: {points_needed}")
                    return {
                        "success": False,
                        "error": "insufficient_points",
                        "message": "积分不足",
                        "current_points": current_points,
                        "required_points": points_needed,
                        "shortfall": points_needed - current_points
                    }
                
                # 使用RPC函数进行积分扣除（绕过RLS）
                new_balance = current_points - points_needed
                transaction_id = str(uuid.uuid4())
                
                # 调用数据库RPC函数进行原子性积分扣除和交易记录
                try:
                    rpc_result = user_points_service.supabase.rpc('consume_user_points', {
                        'p_user_id': user_id,
                        'p_points_to_consume': points_needed,
                        'p_service_type': 'voice_synthesis',
                        'p_description': f"语音合成 - 文本长度: {len(text)}",
                        'p_request_id': f"voice_{user_id}_{int(datetime.now().timestamp())}"
                    }).execute()
                    
                    if rpc_result.data and rpc_result.data.get('success'):
                        points_transaction = {
                            "transaction_id": transaction_id,
                            "points_consumed": points_needed,
                            "points_before": current_points,
                            "points_after": new_balance
                        }
                        if LoggingConfig.should_log_debug():
                            logger.debug(f"积分扣除成功 - 用户: {user_id}, 扣除: {points_needed}, 剩余: {new_balance}")
                    else:
                        logger.error(f"RPC扣除积分失败 - 用户: {user_id}")
                        return {
                            "success": False,
                            "error": "points_deduction_failed",
                            "message": "积分扣除失败"
                        }
                except Exception as rpc_error:
                    logger.warning(f"RPC扣除失败，使用直接更新: {rpc_error}")
                    # 回退到直接更新方式
                    update_response = user_points_service.supabase.table("user_profiles").update({
                        "points": new_balance,
                        "updated_at": datetime.now().isoformat()
                    }).eq("user_id", user_id).execute()
                    
                    if not update_response.data:
                        logger.error(f"积分扣除失败 - 用户: {user_id}")
                        return {
                            "success": False,
                            "error": "points_deduction_failed",
                            "message": "积分扣除失败"
                        }
                    
                    points_transaction = {
                        "transaction_id": transaction_id,
                        "points_consumed": points_needed,
                        "points_before": current_points,
                        "points_after": new_balance
                    }
                    if LoggingConfig.should_log_debug():
                        logger.debug(f"积分扣除成功（直接更新）- 用户: {user_id}, 扣除: {points_needed}, 剩余: {new_balance}")
                
            except Exception as e:
                logger.error(f"积分扣除异常: {e}")
                return {
                    "success": False,
                    "error": "points_processing_error",
                    "message": f"积分处理异常: {str(e)}"
                }
            
        url = f"{self.base_url}?GroupId={self.group_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "speech-2.5-turbo-preview",
            "text": text,
            "stream": False,  # 使用非流式模式
            "voice_setting": {
                "voice_id": voice_id,
                "speed": float(speed),
                "vol": float(volume),
                "pitch": int(pitch) if pitch == int(pitch) else pitch
            },
            "audio_setting": {
                "sample_rate": sample_rate,
                "bitrate": bitrate,
                "format": audio_format,
                "channel": 1
            },
            "pronunciation_dict": {},
            "language_boost": language_boost or "auto"
        }
        
        # 3. 调用Minimax API
        try:
            if LoggingConfig.should_log_debug():
                logger.debug(f"开始转换文本为语音: {text[:50]}...")
                logger.debug(f"语音转换请求参数: {payload}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                try:
                    # Minimax API返回JSON格式，包含十六进制编码的音频数据
                    response_data = response.json()
                    
                    # 检查响应状态
                    if response_data.get('base_resp', {}).get('status_code') == 0:
                        # 获取十六进制编码的音频数据
                        hex_audio = response_data.get('data', {}).get('audio', '')
                        
                        if hex_audio:
                            # 将十六进制字符串转换为字节数据
                            audio_bytes = bytes.fromhex(hex_audio)
                            if LoggingConfig.should_log_debug():
                                logger.debug(f"语音转换成功，音频大小: {len(audio_bytes)} 字节")
                            
                            # 4. 积分已经在consume_points中自动记录了交易，无需额外记录
                            
                            return {
                                "success": True,
                                "audio_data": audio_bytes,
                                "text_length": len(text),
                                "audio_size": len(audio_bytes),
                                "points_transaction": points_transaction
                            }
                        else:
                            logger.error("响应中没有找到音频数据")
                            # 如果扣了积分但生成失败，需要退款
                            if points_transaction:
                                await self._refund_points(user_id, points_transaction, user_points_service)
                            return {
                                "success": False,
                                "error": "no_audio_data",
                                "message": "响应中没有找到音频数据"
                            }
                    else:
                        # API返回错误
                        error_msg = response_data.get('base_resp', {}).get('status_msg', '未知错误')
                        logger.error(f"Minimax API返回错误: {error_msg}")
                        # 如果扣了积分但生成失败，需要退款
                        if points_transaction:
                            await self._refund_points(user_id, points_transaction, user_points_service)
                        return {
                            "success": False,
                            "error": "api_error",
                            "message": f"语音生成失败: {error_msg}"
                        }
                        
                except ValueError as e:
                    # JSON解析失败
                    logger.error(f"响应JSON解析失败: {e}")
                    logger.error(f"响应内容: {response.text[:200]}...")
                    # 如果扣了积分但生成失败，需要退款
                    if points_transaction:
                        await self._refund_points(user_id, points_transaction, user_points_service)
                    return {
                        "success": False,
                        "error": "response_parse_error",
                        "message": "响应解析失败"
                    }
            else:
                logger.error(f"语音转换API调用失败: {response.status_code} - {response.text}")
                # 如果扣了积分但生成失败，需要退款
                if points_transaction:
                    await self._refund_points(user_id, points_transaction, user_points_service)
                return {
                    "success": False,
                    "error": "api_call_failed",
                    "message": f"API调用失败: {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            logger.error("语音转换请求超时")
            # 如果扣了积分但生成失败，需要退款
            if points_transaction:
                await self._refund_points(user_id, points_transaction, user_points_service)
            return {
                "success": False,
                "error": "request_timeout",
                "message": "语音转换请求超时"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"语音转换请求异常: {str(e)}")
            # 如果扣了积分但生成失败，需要退款
            if points_transaction:
                await self._refund_points(user_id, points_transaction, user_points_service)
            return {
                "success": False,
                "error": "request_exception",
                "message": f"网络请求异常: {str(e)}"
            }
        except Exception as e:
            logger.error(f"语音转换未知错误: {str(e)}")
            # 如果扣了积分但生成失败，需要退款
            if points_transaction:
                await self._refund_points(user_id, points_transaction, user_points_service)
            return {
                "success": False,
                "error": "unknown_error",
                "message": f"未知错误: {str(e)}"
            }
    
    def get_supported_language_boost(self) -> Dict[str, Any]:
        """
        获取支持的语言增强选项
        
        Returns:
            支持的语言增强选项字典
        """
        return {
            "supported_languages": list(self.SUPPORTED_LANGUAGE_BOOST),
            "default": "auto",
            "description": "增强对指定的小语种和方言的识别能力，设置后可以提升在指定小语种/方言场景下的语音表现。如果不明确小语种类型，则可以选择'auto'，模型将自主判断小语种类型。"
        }
    
    def get_available_voices(self) -> Dict[str, Any]:
        """
        获取可用的声音列表
        
        Returns:
            可用声音的字典
        """
        voices: Dict[str, Any] = {}
        for category, voice_ids in self.VOICE_CATEGORY_MAP.items():
            entries = []
            for voice_id in voice_ids:
                metadata = self.SUPPORTED_VOICES.get(voice_id)
                if not metadata:
                    continue
                entries.append({
                    "id": voice_id,
                    "name": metadata["name"],
                    "language": metadata["language"],
                    "gender": metadata["gender"],
                })
            voices[category] = entries
        return voices

    def _resolve_voice_id(self, voice_id: Optional[str]) -> Tuple[str, bool, bool]:
        """
        将语音ID解析为受支持的值。
        
        Returns:
            (解析后的ID, 是否使用别名, 是否回退到默认声音)
        """
        raw = (voice_id or "").strip()
        if not raw:
            return self.DEFAULT_VOICE_ID, False, True

        if raw in self.SUPPORTED_VOICES:
            return raw, False, False

        alias_target = self.VOICE_ALIASES.get(raw) or self.VOICE_ALIASES.get(raw.lower())
        if alias_target and alias_target in self.SUPPORTED_VOICES:
            return alias_target, True, False

        return self.DEFAULT_VOICE_ID, False, True

    async def _refund_points(self, user_id: str, points_transaction: Dict[str, Any], points_service_instance = None):
        """退还积分（当语音生成失败时）"""
        try:
            if not points_service_instance:
                logger.error("无法退款：缺少points_service实例")
                return
                
            # 直接恢复积分到原来的数量
            refund_response = points_service_instance.supabase.table("user_profiles").update({
                "points": points_transaction["points_before"],
                "updated_at": datetime.now().isoformat()
            }).eq("user_id", user_id).execute()
            
            if refund_response.data:
                logger.info(f"积分退款成功 - 用户: {user_id}, 退款: {points_transaction['points_consumed']}")
            else:
                logger.error(f"积分退款失败 - 用户: {user_id}")
            
        except Exception as e:
            logger.error(f"积分退款失败: {e}")


# 创建全局语音服务实例
voice_service = VoiceService() 
