"""
AI Agent 模块
专门用于语言学习场景的智能代理
"""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .ai_service import ai_service
from ..core.config import settings

logger = logging.getLogger(__name__)


class LanguageLearningAgent:
    """语言学习AI代理"""
    
    def __init__(self):
        self.ai_service = ai_service
        
    async def explain_text(
        self,
        text: str,
        context: Optional[str] = None,
        user_level: str = "intermediate",
        target_language: str = "zh",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        解释文本内容
        
        Args:
            text: 要解释的文本
            context: 上下文信息
            user_level: 用户水平 (beginner, intermediate, advanced)
            target_language: 目标语言
            provider: AI 提供商
            
        Returns:
            解释结果
        """
        # 根据用户水平调整解释深度
        level_prompts = {
            "beginner": "请用简单易懂的语言",
            "intermediate": "请用中等难度的语言",
            "advanced": "请用专业详细的语言"
        }
        
        level_instruction = level_prompts.get(user_level, level_prompts["intermediate"])
        
        system_prompt = f"""你是一个专业的语言学习助手。{level_instruction}用{target_language}详细解释用户提供的文本。

请从以下角度进行解释：
1. 核心含义和主要观点
2. 重要词汇和短语
3. 语法结构分析
4. 文化背景或使用场景
5. 学习要点和记忆建议

请保持解释的准确性和教育性。"""

        user_message = f"请解释以下文本：\n\n{text}"
        if context:
            user_message += f"\n\n上下文：{context}"
            
        return await self.ai_service.chat_completion(
            message=user_message,
            system_prompt=system_prompt,
            provider=provider
        )
    
    async def translate_and_explain(
        self,
        text: str,
        source_language: str = "auto",
        target_language: str = "zh",
        include_pronunciation: bool = False,
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        翻译并解释文本
        
        Args:
            text: 要翻译的文本
            source_language: 源语言
            target_language: 目标语言
            include_pronunciation: 是否包含发音
            provider: AI 提供商
            
        Returns:
            翻译和解释结果
        """
        pronunciation_instruction = ""
        if include_pronunciation:
            pronunciation_instruction = "请提供关键词汇的发音指南（拼音或音标）。"
        
        system_prompt = f"""你是一个专业的翻译和语言学习助手。请将文本从{source_language}翻译成{target_language}，并提供详细的解释。

请按以下格式输出：
1. 翻译结果
2. 直译对比（如果有必要）
3. 关键词汇解释
4. 语法要点
5. 使用场景和语域
{pronunciation_instruction}

请确保翻译准确自然，解释清晰易懂。"""

        return await self.ai_service.chat_completion(
            message=f"请翻译并解释：{text}",
            system_prompt=system_prompt,
            provider=provider
        )
    
    async def generate_study_questions(
        self,
        text: str,
        question_types: List[str] = None,
        difficulty: str = "intermediate",
        count: int = 5,
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        根据文本生成学习问题
        
        Args:
            text: 基础文本
            question_types: 问题类型列表
            difficulty: 难度级别
            count: 问题数量
            provider: AI 提供商
            
        Returns:
            学习问题列表
        """
        if question_types is None:
            question_types = ["理解", "词汇", "语法", "应用"]
        
        types_str = "、".join(question_types)
        
        system_prompt = f"""你是一个专业的语言学习内容生成助手。请基于给定文本生成{count}个学习问题。

问题要求：
- 涵盖类型：{types_str}
- 难度级别：{difficulty}
- 格式：问题 + 参考答案
- 目标：帮助学习者深入理解和掌握文本内容

请确保问题有教育价值，答案准确完整。"""

        return await self.ai_service.chat_completion(
            message=f"请基于以下文本生成学习问题：\n\n{text}",
            system_prompt=system_prompt,
            provider=provider
        )
    
    async def vocabulary_extraction(
        self,
        text: str,
        difficulty_level: str = "all",
        include_definitions: bool = True,
        include_examples: bool = True,
        target_language: str = "zh",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        提取文本中的重要词汇
        
        Args:
            text: 源文本
            difficulty_level: 词汇难度级别
            include_definitions: 是否包含定义
            include_examples: 是否包含例句
            target_language: 解释语言
            provider: AI 提供商
            
        Returns:
            词汇提取结果
        """
        options = []
        if include_definitions:
            options.append(f"用{target_language}提供清晰的定义")
        if include_examples:
            options.append("提供使用例句")
            
        options_str = "、".join(options) if options else "仅列出词汇"
        
        system_prompt = f"""你是一个专业的词汇分析助手。请从文本中提取重要词汇。

提取要求：
- 难度级别：{difficulty_level}
- 输出内容：{options_str}
- 按重要性排序
- 包含词性标注

请确保选择的词汇对语言学习有价值。"""

        return await self.ai_service.chat_completion(
            message=f"请提取以下文本中的重要词汇：\n\n{text}",
            system_prompt=system_prompt,
            provider=provider
        )
    
    async def conversation_practice(
        self,
        topic: str,
        user_response: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        language_focus: str = "zh",
        provider: str = "gemini"
    ) -> Dict[str, Any]:
        """
        对话练习功能
        
        Args:
            topic: 对话主题
            user_response: 用户回应
            conversation_history: 对话历史
            language_focus: 重点语言
            provider: AI 提供商
            
        Returns:
            对话练习反馈
        """
        system_prompt = f"""你是一个友好的{language_focus}对话练习伙伴。主题是：{topic}

你的任务：
1. 自然地回应用户的发言
2. 适当纠正语言错误（温和提醒）
3. 提供更好的表达建议
4. 引导对话继续进行
5. 鼓励用户多说多练

请保持对话轻松愉快，同时具有教育价值。"""

        return await self.ai_service.chat_completion(
            message=user_response,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            provider=provider
        )


# 创建全局语言学习代理实例
language_agent = LanguageLearningAgent() 