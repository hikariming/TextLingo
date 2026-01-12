"""
AI 服务模块
提供基于 LangChain 的 AI 功能，包括 Gemini 和 OpenRouter 集成
"""

import logging
from typing import Optional, Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

from ..core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI 服务类，管理不同的 LLM 提供商"""
    
    def __init__(self):
        self.gemini_client = None
        self.openrouter_client = None
        self._init_clients()
    
    def _init_clients(self):
        """初始化 AI 客户端"""
        try:
            # 初始化 Gemini
            if settings.google_api_key:
                self.gemini_client = ChatGoogleGenerativeAI(
                    model=settings.default_gemini_model,
                    google_api_key=settings.google_api_key,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                )
                logger.info("Gemini client initialized successfully")
            
            # 初始化 OpenRouter
            if settings.openrouter_api_key:
                self.openrouter_client = ChatOpenAI(
                    model=settings.default_openrouter_model,
                    openai_api_key=settings.openrouter_api_key,
                    openai_api_base=settings.openrouter_base_url,
                    temperature=settings.temperature,
                    max_tokens=settings.max_tokens,
                )
                logger.info("OpenRouter client initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize AI clients: {e}")
    
    async def chat_completion(
        self,
        message: str,
        system_prompt: Optional[str] = None,
        provider: str = "gemini",
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        执行聊天完成
        
        Args:
            message: 用户消息
            system_prompt: 系统提示词
            provider: AI 提供商 ("gemini" 或 "openrouter")
            conversation_history: 对话历史
            
        Returns:
            包含AI响应和元数据的字典
        """
        try:
            # 选择客户端
            client = self._get_client(provider)
            if not client:
                raise ValueError(f"Provider {provider} not available")
            
            # 构建消息
            messages = []
            
            # 添加系统消息
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            
            # 添加对话历史
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            # 添加当前用户消息
            messages.append(HumanMessage(content=message))
            
            # 调用 AI
            response = await client.ainvoke(messages)
            
            return {
                "success": True,
                "content": response.content,
                "provider": provider,
                "model": client.model_name if hasattr(client, 'model_name') else "unknown",
                "usage": getattr(response, 'usage_metadata', None)
            }
            
        except Exception as e:
            logger.error(f"Chat completion failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": provider
            }
    
    def _get_client(self, provider: str):
        """获取指定的 AI 客户端"""
        if provider == "gemini":
            return self.gemini_client
        elif provider == "openrouter":
            return self.openrouter_client
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def text_analysis(
        self,
        text: str,
        analysis_type: str = "explain",
        target_language: str = "zh",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        文本分析功能
        
        Args:
            text: 要分析的文本
            analysis_type: 分析类型 ("explain", "translate", "summarize")
            target_language: 目标语言
            provider: AI 提供商
            
        Returns:
            分析结果
        """
        # 构建系统提示词
        system_prompts = {
            "explain": f"你是一个专业的语言学习助手。请用{target_language}详细解释用户提供的文本内容，包括词汇、语法、文化背景等。",
            "translate": f"你是一个专业的翻译助手。请将用户提供的文本准确翻译成{target_language}，并简要说明翻译要点。",
            "summarize": f"你是一个专业的文本总结助手。请用{target_language}对用户提供的文本进行简洁而全面的总结。"
        }
        
        system_prompt = system_prompts.get(analysis_type, system_prompts["explain"])
        
        return await self.chat_completion(
            message=f"请分析以下文本：\n\n{text}",
            system_prompt=system_prompt,
            provider=provider
        )
    
    def get_available_providers(self) -> List[str]:
        """获取可用的 AI 提供商列表"""
        providers = []
        if self.gemini_client:
            providers.append("gemini")
        if self.openrouter_client:
            providers.append("openrouter")
        return providers


# 创建全局 AI 服务实例
ai_service = AIService()
