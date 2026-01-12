"""
改进的分段算法示例
"""

import re
from typing import List, Tuple

class ImprovedSegmentation:
    """智能分段算法，优先保持内容完整性"""
    
    def __init__(self, target_size: int = 10000, max_size: int = 12000):
        self.target_size = target_size
        self.max_size = max_size
        
    def smart_segment(self, text: str) -> List[Tuple[str, int, int]]:
        """
        智能分段，返回 (segment_text, start_pos, end_pos) 列表
        
        优先级：
        1. 章节边界（=== Chapter ===）
        2. 双换行（段落边界）
        3. 句号边界
        4. 其他标点
        5. 字符数限制
        """
        segments = []
        current_pos = 0
        
        while current_pos < len(text):
            # 计算理想的结束位置
            ideal_end = min(current_pos + self.target_size, len(text))
            max_end = min(current_pos + self.max_size, len(text))
            
            # 如果已经到文本末尾
            if ideal_end >= len(text):
                segments.append((text[current_pos:], current_pos, len(text)))
                break
                
            # 查找最佳分割点
            best_split = self._find_best_split_point(
                text, current_pos, ideal_end, max_end
            )
            
            segments.append((text[current_pos:best_split], current_pos, best_split))
            current_pos = best_split
            
        return segments
    
    def _find_best_split_point(self, text: str, start: int, ideal: int, max_pos: int) -> int:
        """找到最佳分割点"""
        
        # 1. 检查章节边界
        chapter_pattern = r'\n\n===.*?===\n\n'
        for match in re.finditer(chapter_pattern, text[ideal:max_pos]):
            return ideal + match.start()
            
        # 2. 检查段落边界（双换行）
        paragraph_pos = text.rfind('\n\n', start, max_pos)
        if paragraph_pos > ideal:
            return paragraph_pos + 2
            
        # 3. 检查句子边界
        sentence_endings = ['. ', '。', '! ', '！', '? ', '？']
        best_sentence_pos = -1
        for ending in sentence_endings:
            pos = text.rfind(ending, ideal, max_pos)
            if pos > best_sentence_pos:
                best_sentence_pos = pos + len(ending)
                
        if best_sentence_pos > ideal:
            return best_sentence_pos
            
        # 4. 检查其他标点
        punctuation = ['，', ', ', '；', '; ', '：', ': ']
        best_punct_pos = -1
        for punct in punctuation:
            pos = text.rfind(punct, ideal, max_pos)
            if pos > best_punct_pos:
                best_punct_pos = pos + len(punct)
                
        if best_punct_pos > ideal:
            return best_punct_pos
            
        # 5. 如果都没找到，在空格处分割
        space_pos = text.rfind(' ', ideal, max_pos)
        if space_pos > ideal:
            return space_pos + 1
            
        # 6. 最后选择：直接在max_pos分割
        return max_pos