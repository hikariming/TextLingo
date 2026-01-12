"""
EPUB格式保留处理示例
"""

import html2text
from typing import Dict, Any

class FormatPreservingEpubConverter:
    """保留基本格式的EPUB转换器"""
    
    def __init__(self):
        # 配置html2text保留更多格式
        self.h = html2text.HTML2Text()
        self.h.body_width = 0  # 不自动换行
        self.h.unicode_snob = True  # 使用Unicode字符
        self.h.emphasis_mark = '*'  # 斜体标记
        self.h.strong_mark = '**'  # 粗体标记
        self.h.ul_item_mark = '• '  # 列表标记
        self.h.links_each_paragraph = True
        self.h.skip_internal_links = False
        
    def convert_with_format(self, html_content: str) -> Dict[str, Any]:
        """
        转换HTML内容，保留格式信息
        
        返回：
        - text: 带Markdown格式的文本
        - metadata: 额外的格式信息
        """
        # 预处理HTML，保留特殊格式
        processed_html = self._preprocess_html(html_content)
        
        # 转换为Markdown格式文本
        markdown_text = self.h.handle(processed_html)
        
        # 提取特殊格式元数据
        metadata = self._extract_metadata(html_content)
        
        return {
            'text': markdown_text,
            'metadata': metadata
        }
    
    def _preprocess_html(self, html: str) -> str:
        """预处理HTML以更好地保留格式"""
        # 保留思考/内心独白的斜体
        html = html.replace('<i>', '*').replace('</i>', '*')
        html = html.replace('<em>', '*').replace('</em>', '*')
        
        # 保留强调的粗体
        html = html.replace('<b>', '**').replace('</b>', '**')
        html = html.replace('<strong>', '**').replace('</strong>', '**')
        
        # 保留引用
        html = html.replace('<blockquote>', '\n> ').replace('</blockquote>', '\n')
        
        return html
    
    def _extract_metadata(self, html: str) -> Dict[str, Any]:
        """提取额外的格式元数据"""
        return {
            'has_italics': '<i>' in html or '<em>' in html,
            'has_bold': '<b>' in html or '<strong>' in html,
            'has_quotes': '<blockquote>' in html,
            'has_links': '<a href=' in html
        }