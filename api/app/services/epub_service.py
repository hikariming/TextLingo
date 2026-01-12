"""
EPUB文件处理服务
支持从EPUB文件中提取文本内容、章节结构和元数据
"""

import ebooklib
from ebooklib import epub
import html2text
import re
from typing import List, Dict, Any, Tuple, Optional
import structlog
from dataclasses import dataclass
from io import BytesIO
import tempfile
import os

logger = structlog.get_logger()


@dataclass
class EpubChapter:
    """EPUB章节数据结构"""
    title: str
    content: str
    order: int
    char_count: int
    paragraph_count: int
    sentence_count: int


@dataclass
class EpubMetadata:
    """EPUB元数据结构"""
    title: str
    author: Optional[str] = None
    language: str = "en"
    description: Optional[str] = None


@dataclass
class EpubParseResult:
    """EPUB解析结果"""
    metadata: EpubMetadata
    chapters: List[EpubChapter]
    warnings: List[str]


class EpubService:
    """EPUB文件处理服务"""
    
    def __init__(self):
        # 配置html2text转换器
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0  # 不限制行宽
        
    async def parse_epub_file(self, file_content: bytes) -> EpubParseResult:
        """
        解析EPUB文件，提取章节和元数据
        
        Args:
            file_content: EPUB文件的二进制内容
            
        Returns:
            EpubParseResult: 解析结果，包含元数据、章节和警告信息
        """
        try:
            warnings = []
            
            # 创建临时文件来存储EPUB内容，因为ebooklib需要文件路径
            with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # 读取EPUB文件
                book = epub.read_epub(temp_file_path)
                
                # 提取元数据
                metadata = self._extract_metadata(book)
                logger.info("Extracted EPUB metadata", title=metadata.title, author=metadata.author)
                
                # 提取章节内容
                chapters = self._extract_chapters(book, warnings)
                
                if not chapters:
                    warnings.append("未能从EPUB文件中提取到任何章节内容")
                    
                logger.info("EPUB parsing completed", 
                           chapters_count=len(chapters), 
                           warnings_count=len(warnings))
                
                return EpubParseResult(
                    metadata=metadata,
                    chapters=chapters,
                    warnings=warnings
                )
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file_path)
                except OSError:
                    pass
            
        except Exception as e:
            logger.error(f"Error parsing EPUB file: {e}")
            raise Exception(f"EPUB文件解析失败: {str(e)}")
    
    def _extract_metadata(self, book: epub.EpubBook) -> EpubMetadata:
        """提取EPUB元数据"""
        try:
            # 提取标题
            title = "未知标题"
            if book.get_metadata('DC', 'title'):
                title = book.get_metadata('DC', 'title')[0][0]
            
            # 提取作者
            author = None
            if book.get_metadata('DC', 'creator'):
                author = book.get_metadata('DC', 'creator')[0][0]
            
            # 提取语言
            language = "en"
            if book.get_metadata('DC', 'language'):
                language = book.get_metadata('DC', 'language')[0][0]
            
            # 提取描述
            description = None
            if book.get_metadata('DC', 'description'):
                description = book.get_metadata('DC', 'description')[0][0]
            
            return EpubMetadata(
                title=title,
                author=author,
                language=language,
                description=description
            )
            
        except Exception as e:
            logger.warning(f"Error extracting EPUB metadata: {e}")
            return EpubMetadata(title="未知标题")
    
    def _extract_chapters(self, book: epub.EpubBook, warnings: List[str]) -> List[EpubChapter]:
        """提取章节内容"""
        chapters = []
        chapter_order = 0
        
        try:
            # 获取所有文档项目
            documents = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    documents.append(item)
            
            # 按照spine顺序排序章节
            spine_ids = [spine_item[0] for spine_item in book.spine]
            ordered_documents = []
            
            # 按spine顺序添加文档
            for spine_id in spine_ids:
                for doc in documents:
                    if doc.get_id() == spine_id:
                        ordered_documents.append(doc)
                        break
            
            # 如果没有spine信息，直接使用文档列表
            if not ordered_documents:
                ordered_documents = documents
                warnings.append("EPUB文件没有spine信息，使用默认章节顺序")
            
            # 处理每个文档
            for doc in ordered_documents:
                try:
                    chapter = self._process_document(doc, chapter_order)
                    if chapter and chapter.content.strip():
                        chapters.append(chapter)
                        chapter_order += 1
                    else:
                        warnings.append(f"章节 {doc.get_name()} 内容为空，已跳过")
                        
                except Exception as e:
                    warnings.append(f"处理章节 {doc.get_name()} 时出错: {str(e)}")
                    continue
            
            return chapters
            
        except Exception as e:
            logger.error(f"Error extracting chapters: {e}")
            warnings.append(f"提取章节时出错: {str(e)}")
            return []
    
    def _process_document(self, document: epub.EpubHtml, order: int) -> Optional[EpubChapter]:
        """处理单个EPUB文档，转换为章节"""
        try:
            # 获取HTML内容并尝试多种编码
            raw_content = document.get_content()
            html_content = None
            
            # 首先尝试检测HTML中声明的编码
            detected_encoding = self._detect_html_encoding(raw_content)
            if detected_encoding:
                try:
                    html_content = raw_content.decode(detected_encoding)
                    logger.debug(f"Successfully decoded {document.get_name()} using detected encoding: {detected_encoding}")
                except UnicodeDecodeError:
                    logger.warning(f"Failed to decode with detected encoding {detected_encoding}, trying other encodings")
            
            # 如果检测的编码失败或没有检测到，尝试常见编码
            if html_content is None:
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin-1', 'shift_jis', 'euc-jp', 'cp1252']
                for encoding in encodings:
                    try:
                        html_content = raw_content.decode(encoding)
                        logger.debug(f"Successfully decoded {document.get_name()} using {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
            
            if html_content is None:
                # 如果所有编码都失败，尝试忽略错误
                html_content = raw_content.decode('utf-8', errors='ignore')
                logger.warning(f"Had to decode {document.get_name()} with errors ignored")
            
            # 提取标题
            title = self._extract_chapter_title(html_content, document.get_name())
            
            # 将HTML转换为纯文本
            text_content = self.html_converter.handle(html_content)
            
            # 清理文本
            cleaned_content = self._clean_text_content(text_content)
            
            if not cleaned_content.strip():
                return None
            
            # 计算统计信息
            char_count = len(cleaned_content)
            paragraph_count = len([p for p in cleaned_content.split('\n\n') if p.strip()])
            sentence_count = len(re.findall(r'[.!?]+', cleaned_content))
            
            return EpubChapter(
                title=title,
                content=cleaned_content,
                order=order,
                char_count=char_count,
                paragraph_count=paragraph_count,
                sentence_count=sentence_count
            )
            
        except Exception as e:
            logger.warning(f"Error processing document {document.get_name()}: {e}")
            return None
    
    def _detect_html_encoding(self, raw_html: bytes) -> Optional[str]:
        """从HTML内容中检测编码"""
        # 尝试用ASCII解码来查找meta标签中的charset
        try:
            # 只解析前1000个字节来查找编码声明
            header = raw_html[:1000].decode('ascii', errors='ignore').lower()
            
            # 查找HTML meta标签中的charset
            charset_patterns = [
                r'<meta[^>]+charset\s*=\s*["\']?([^"\'>\s]+)',
                r'<meta[^>]+content\s*=\s*["\'][^"\']*charset\s*=\s*([^"\'>\s;]+)',
                r'encoding\s*=\s*["\']([^"\']+)["\']'  # XML声明
            ]
            
            for pattern in charset_patterns:
                match = re.search(pattern, header)
                if match:
                    encoding = match.group(1).strip()
                    # 标准化编码名称
                    encoding_map = {
                        'utf8': 'utf-8',
                        'shift-jis': 'shift_jis',
                        'windows-1252': 'cp1252',
                        'iso-8859-1': 'latin-1'
                    }
                    return encoding_map.get(encoding.lower(), encoding.lower())
        except:
            pass
        
        return None
    
    def _extract_chapter_title(self, html_content: str, filename: str) -> str:
        """从HTML内容中提取章节标题"""
        try:
            # 尝试从HTML中提取标题
            title_patterns = [
                r'<h1[^>]*>(.*?)</h1>',
                r'<h2[^>]*>(.*?)</h2>',
                r'<h3[^>]*>(.*?)</h3>',
                r'<title[^>]*>(.*?)</title>',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if match:
                    title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                    if title and len(title) < 200:  # 合理的标题长度
                        return title
            
            # 如果没有找到标题，使用文件名生成标题
            base_name = filename.replace('.xhtml', '').replace('.html', '').replace('.htm', '')
            
            # 尝试从文件名中提取章节信息
            chapter_match = re.search(r'(chapter|ch|第).*?(\d+)', base_name, re.IGNORECASE)
            if chapter_match:
                chapter_num = chapter_match.group(2)
                return f"第 {chapter_num} 章"
            
            # 使用清理后的文件名
            clean_name = re.sub(r'[_-]+', ' ', base_name).title()
            return clean_name if clean_name else f"章节 {filename}"
            
        except Exception as e:
            logger.warning(f"Error extracting chapter title: {e}")
            return f"章节 {filename}"
    
    def _clean_text_content(self, text_content: str) -> str:
        """清理文本内容"""
        try:
            # 移除markdown格式标记
            content = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', text_content)
            content = re.sub(r'_{1,2}([^_]+)_{1,2}', r'\1', content)
            
            # 清理多余的换行符
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # 清理行首行尾空格
            lines = []
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    lines.append(line)
                elif lines and lines[-1]:  # 保留段落间的空行
                    lines.append('')
            
            # 重新组合内容
            content = '\n'.join(lines)
            
            # 移除文件开头和结尾的多余空行
            content = content.strip()
            
            return content
            
        except Exception as e:
            logger.warning(f"Error cleaning text content: {e}")
            return text_content
    
    def convert_to_segmentation_format(self, chapters: List[EpubChapter]) -> str:
        """将章节列表转换为分段处理格式"""
        try:
            if not chapters:
                logger.warning("No chapters provided for segmentation format conversion")
                return ""
            
            # 将所有章节内容合并，每个章节之间用特殊分隔符分开
            combined_content = []
            valid_chapters = 0
            
            for i, chapter in enumerate(chapters):
                if not chapter or not chapter.content or not chapter.content.strip():
                    logger.warning(f"Chapter {i} is empty or has no content: {chapter.title if chapter else 'None'}")
                    continue
                
                # 验证章节内容不包含二进制数据
                try:
                    chapter.content.encode('utf-8')
                except UnicodeEncodeError:
                    logger.error(f"Chapter {i} ({chapter.title}) contains invalid characters")
                    continue
                
                # 添加章节标题作为分隔标记
                chapter_header = f"\n\n=== {chapter.title} ===\n\n"
                combined_content.append(chapter_header)
                combined_content.append(chapter.content)
                valid_chapters += 1
            
            if valid_chapters == 0:
                raise ValueError("所有章节都无效或为空")
            
            result = ''.join(combined_content)
            logger.info(f"Converted {valid_chapters}/{len(chapters)} chapters to segmentation format, total length: {len(result)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error converting chapters to segmentation format: {e}")
            raise
    
    @staticmethod
    def is_epub_file(file_content: bytes) -> bool:
        """检查文件是否为EPUB格式"""
        try:
            # EPUB文件是ZIP格式，检查ZIP文件头
            if len(file_content) < 4:
                return False
            
            # 检查ZIP文件头 (PK)
            if file_content[0:2] != b'PK':
                return False
            
            # 尝试读取为EPUB文件
            try:
                with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_file_path = temp_file.name
                
                try:
                    book = epub.read_epub(temp_file_path)
                    return True
                finally:
                    try:
                        os.unlink(temp_file_path)
                    except OSError:
                        pass
            except:
                return False
                
        except Exception:
            return False
    
    @staticmethod
    def get_supported_extensions() -> List[str]:
        """获取支持的文件扩展名"""
        return ['.epub']
    
    @staticmethod
    def get_supported_mime_types() -> List[str]:
        """获取支持的MIME类型"""
        return ['application/epub+zip']


# 创建单例实例
epub_service = EpubService()