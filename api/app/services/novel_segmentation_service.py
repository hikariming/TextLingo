"""
小说分段服务
支持多种分段模式：正则表达式、语义、段落、句子、字符
支持分层分段逻辑和最大字符数限制
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import structlog
from app.schemas.novel_segmentation_schemas import SegmentationMode, SegmentInfo

logger = structlog.get_logger()

@dataclass
class SegmentationConfig:
    """Internal segmentation configuration dataclass, mirrors the request model."""
    primary_segmentation_mode: SegmentationMode
    secondary_segmentation_mode: Optional[SegmentationMode]
    max_chars_per_segment: int
    language: str
    custom_regex_separators: Optional[List[str]]
    characters_per_segment: int
    paragraphs_per_segment: int
    sentences_per_segment: int

@dataclass
class TempSegment:
    """临时分段对象，用于处理过程"""
    title: str
    content: str
    order: int = 0
    is_split: bool = False # 标记是否由超长分割产生

@dataclass
class SegmentationResult:
    """完整分段结果，包含分段和警告"""
    segments: List[SegmentInfo]
    warnings: List[str] = field(default_factory=list)


class NovelSegmentationService:
    """小说分段服务类"""
    
    def __init__(self):
        # 为“semantic”模式预定义语言特定的正则表达式
        self.language_chapter_patterns = {
            "zh": [
                r"(第\s*[一二三四五六七八九十百千万\d]+\s*[章节回篇部卷集])",
                r"([章节回篇部卷集]\s*[一二三四五六七八九十百千万\d]+)",
                r"(序章|终章|尾声|后记|前言|序|引子)"
            ],
            "ja": [
                r"^\s*(第\s*\d+\s*[章話话編编部巻卷])\s*.*$",
                r"^\s*([章話话編编部巻卷]\s*\d+)\s*.*$",
                r"^\s*(プロローグ|エピローグ|序章|終章|最終章)\s*.*$"
            ],
            "en": [
                r"^\s*(Chapter|Part|Section|Book|Volume)\s+\d+\s*.*$",
                r"^\s*(Prologue|Epilogue|Preface|Conclusion)\s*.*$"
            ],
            "ko": [
                r"^\s*(제\s*\d+\s*[장편부권화])\s*.*$",
                r"^\s*(프롤로그|에필로그|서장|종장)\s*.*$"
            ]
        }

    async def segment_text(self, text: str, config: SegmentationConfig) -> SegmentationResult:
        """
        根据配置对文本进行分段，采用分层逻辑
        1. 主分段：按章节（REGEX或SEMANTIC）
        2. 次级分段：处理超长章节（PARAGRAPH, SENTENCE, CHARACTER）
        3. 硬切分：最后的保险措施
        """
        try:
            logger.info("Starting hierarchical text segmentation", config=config)
            
            # 1. 执行主分段 (章节级)
            primary_segments = await self._perform_primary_segmentation(text, config)
            
            # 2. 处理和切分超长章节
            final_segments: List[TempSegment] = []
            warnings: List[str] = []
            
            for segment in primary_segments:
                if len(segment.content) > config.max_chars_per_segment:
                    warning_msg = (
                        f"章节 '{segment.title}' (长约 {len(segment.content)} 字) "
                        f"因超出最大长度 {config.max_chars_per_segment} 字而被自动切分。"
                    )
                    warnings.append(warning_msg)
                    logger.warning(warning_msg)
                    
                    # 执行次级分段
                    sub_segments = await self._perform_secondary_segmentation(segment.content, config)
                    
                    # 为子分段生成新标题
                    for i, sub_seg in enumerate(sub_segments):
                        final_segments.append(TempSegment(
                            title=f"{segment.title} - Part {i+1}",
                            content=sub_seg.content,
                            is_split=True
                        ))
                else:
                    final_segments.append(segment)
            
            # 3. 重新编号并创建最终的SegmentInfo列表
            final_segment_infos = []
            for i, seg in enumerate(final_segments):
                final_segment_infos.append(self._create_segment_info(
                    id=f"seg-{i:04d}",
                    title=seg.title,
                    content=seg.content,
                    order=i
                ))

            logger.info(f"Segmentation completed. Generated {len(final_segment_infos)} segments.", warnings=warnings)
            return SegmentationResult(segments=final_segment_infos, warnings=warnings)
            
        except Exception as e:
            logger.error("Error during text segmentation", error=str(e), exc_info=True)
            raise

    async def _perform_primary_segmentation(self, text: str, config: SegmentationConfig) -> List[TempSegment]:
        """执行主分段（章节级）"""
        mode = config.primary_segmentation_mode
        
        if mode == SegmentationMode.REGEX:
            if not config.custom_regex_separators:
                raise ValueError("REGEX模式需要提供自定义正则表达式 'custom_regex_separators'")
            return await self._split_by_regex(text, config.custom_regex_separators)
            
        elif mode == SegmentationMode.SEMANTIC:
            patterns = self.language_chapter_patterns.get(config.language, [])
            if not patterns:
                raise ValueError(f"不支持的语言 '{config.language}' 或该语言没有预设的语义分段规则")
            return await self._split_by_regex(text, patterns)
            
        elif mode == SegmentationMode.AUTO_SIMPLE:
            return await self._segment_by_auto_simple(text, config)
            
        elif mode == SegmentationMode.CHARACTER:
            return await self._segment_by_character(text, config)
            
        elif mode == SegmentationMode.PARAGRAPH:
            return await self._segment_by_paragraph(text, config)
            
        elif mode == SegmentationMode.SENTENCE:
            return await self._segment_by_sentence(text, config)
            
        else:
            # 默认情况：将整个文本视为一个分段
            return [TempSegment(title="全文", content=text)]

    async def _perform_secondary_segmentation(self, text: str, config: SegmentationConfig) -> List[TempSegment]:
        """
        对超长文本执行次级分段
        """
        mode = config.secondary_segmentation_mode
        
        # 准备一个临时的配置用于次级分段
        temp_config = SegmentationConfig(
            primary_segmentation_mode=mode, # 使用次级模式作为临时主模式
            max_chars_per_segment=config.max_chars_per_segment,
            paragraphs_per_segment=config.paragraphs_per_segment,
            sentences_per_segment=config.sentences_per_segment,
            characters_per_segment=config.characters_per_segment,
            language=config.language,
            #
            secondary_segmentation_mode=None,
            custom_regex_separators=None
        )
        
        segments: List[TempSegment] = []
        if mode == SegmentationMode.PARAGRAPH:
            segments = await self._segment_by_paragraph(text, temp_config)
        elif mode == SegmentationMode.SENTENCE:
            segments = await self._segment_by_sentence(text, temp_config)
        else: # 默认或指定CHARACTER
            segments = await self._segment_by_character(text, temp_config)

        # 最终检查：确保没有子分段仍然超长
        final_sub_segments: List[TempSegment] = []
        for seg in segments:
            if len(seg.content) > config.max_chars_per_segment:
                logger.warning(f"Sub-segment still too long after secondary segmentation. Applying hard split.",
                               title=seg.title, length=len(seg.content))
                # 使用character模式硬切分
                hard_split_segments = await self._segment_by_character(seg.content, temp_config)
                final_sub_segments.extend(hard_split_segments)
            else:
                final_sub_segments.append(seg)
                
        return final_sub_segments
    
    async def _split_by_regex(self, text: str, patterns: List[str]) -> List[TempSegment]:
        """根据正则表达式列表将文本分割成章节"""
        # 合并所有pattern为一个大的正则表达式
        combined_pattern = f"({'|'.join(patterns)})"
        
        # 使用正则表达式分割文本，保留分隔符（章节标题）
        parts = re.split(combined_pattern, text, flags=re.MULTILINE | re.IGNORECASE)
        
        segments = []
        
        # 第一个部分是引言或前言
        if parts[0].strip():
            segments.append(TempSegment(title="引言", content=parts[0].strip()))
        
        # 匹配项是成对出现的 (标题, 内容)
        for i in range(1, len(parts), 2):
            title = parts[i].strip() if parts[i] else ""
            content = parts[i+1].strip() if (i+1) < len(parts) and parts[i+1] else ""
            if content:
                 segments.append(TempSegment(title=title, content=content))
        
        if not segments and text.strip():
             # 如果没有匹配到任何章节，则将全部内容作为一个分段
            return [TempSegment(title="全文", content=text.strip())]

        return segments

    async def preview_segmentation(self, text: str, config: SegmentationConfig, max_segments: int = 5) -> Dict[str, Any]:
        """预览分段效果，返回包含预览内容和警告的字典"""
        try:
            result = await self.segment_text(text, config)
            
            preview_content = []
            for segment in result.segments[:max_segments]:
                content_preview = segment.content[:200]
                if len(segment.content) > 200:
                    content_preview += "..."
                preview_content.append(f"【{segment.title}】\n{content_preview}")
            
            return {
                "total_segments": len(result.segments),
                "preview_segments": preview_content,
                "warnings": result.warnings
            }
            
        except Exception as e:
            logger.error("Error during segmentation preview", error=str(e), exc_info=True)
            raise

    async def _segment_by_character(self, text: str, config: SegmentationConfig) -> List[TempSegment]:
        """字符数分段：按固定字符数分段 (硬切分)"""
        target_size = config.characters_per_segment
        segments = []
        start = 0
        
        while start < len(text):
            end = min(start + target_size, len(text))
            
            # 为了避免破坏句子，尝试在硬切分前找到一个自然的断点
            if end < len(text):
                # 从end向前找最近的句号
                sentence_end = text.rfind('.', start, end)
                if sentence_end != -1:
                    end = sentence_end + 1
            
            content = text[start:end].strip()
            if content:
                segments.append(TempSegment(title=f"片段", content=content))
            start = end
            
        return segments

    async def _segment_by_paragraph(self, text: str, config: SegmentationConfig) -> List[TempSegment]:
        """段落分段：按段落数量分段"""
        paragraphs_per_segment = config.paragraphs_per_segment
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
        
        segments = []
        for i in range(0, len(paragraphs), paragraphs_per_segment):
            segment_paragraphs = paragraphs[i:i + paragraphs_per_segment]
            content = '\n\n'.join(segment_paragraphs)
            if content:
                segments.append(TempSegment(title=f"段落集", content=content))
                
        return segments

    async def _segment_by_sentence(self, text: str, config: SegmentationConfig) -> List[TempSegment]:
        """句子分段：按句子数量分段"""
        sentences_per_segment = config.sentences_per_segment
        # 更稳健的句子分割正则
        sentence_pattern = r'([^。！？.!?]+[。！？.!?]+)'
        sentences = re.findall(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences and text: # 如果正则没匹配到，做一个简单的回退
            sentences = [text]

        segments = []
        for i in range(0, len(sentences), sentences_per_segment):
            segment_sentences = sentences[i:i + sentences_per_segment]
            content = ''.join(segment_sentences)
            if content:
                segments.append(TempSegment(title=f"句子集", content=content))
                
        return segments

    async def _segment_by_auto_simple(self, text: str, config: SegmentationConfig) -> List[TempSegment]:
        """
        自动简单分段：按10000字符分段，在换行符处切分以避免语义断裂
        """
        target_size = 10000  # 固定10000字符
        segments = []
        start = 0
        segment_number = 1
        
        while start < len(text):
            end = min(start + target_size, len(text))
            
            # 如果没有到达文本末尾，尝试在换行符处切分
            if end < len(text):
                # 从目标位置向后找最近的换行符（最多向后找500字符）
                newline_pos = text.find('\n', end, min(end + 500, len(text)))
                if newline_pos != -1:
                    end = newline_pos + 1  # 包含换行符
                else:
                    # 如果500字符内没有换行符，向前找换行符（最多向前找500字符）
                    newline_pos = text.rfind('\n', max(start, end - 500), end)
                    if newline_pos != -1:
                        end = newline_pos + 1  # 包含换行符
            
            content = text[start:end].strip()
            if content:
                segments.append(TempSegment(
                    title=f"第{segment_number}部分", 
                    content=content
                ))
                segment_number += 1
            
            start = end
        
        logger.info(f"Auto simple segmentation completed. Generated {len(segments)} segments.")
        return segments

    def _create_segment_info(self, id: str, title: str, content: str, order: int) -> SegmentInfo:
        """创建最终的分段信息对象，并计算统计数据"""
        char_count = len(content)
        paragraph_count = len([p for p in content.split('\n\n') if p.strip()])
        sentence_count = len(re.findall(r'[。！？.!?]+', content))
        
        return SegmentInfo(
            id=id,
            title=title,
            content=content,
            order=order,
            char_count=char_count,
            paragraph_count=paragraph_count,
            sentence_count=sentence_count
        ) 