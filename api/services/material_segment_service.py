from models.material_segment import MaterialSegment, VocabularyItem
import re

class MaterialSegmentService:
    @staticmethod
    def segment_text(material_id, text, segmentation_type='paragraph'):
        """
        将文本按照不同方式分段
        支持:
        - paragraph: 按句号(。.)和换行符(\n)分段，换行后的段落标记为新段落
        - punctuation: 按标点符号分段 (。.!?！？\n)
        - linebreak: 按换行符分段 (\n)
        - ai: 智能分段 (TODO)
        """
        processed_segments = []
        is_new_paragraph_flags = []  # 新增一个列表来跟踪每个段落是否是新段落
        
        if segmentation_type == 'paragraph':
            # 首先按换行符分割
            lines = text.split('\n')
            
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

        elif segmentation_type == 'punctuation':
            # 定义分隔符模式
            separators = r'([。.!\?！？\n])'
            
            # 使用正则表达式分割文本
            segments = re.split(separators, text)
            
            # 合并分隔符与其前面的文本
            current_segment = ""
            
            for i, segment in enumerate(segments):
                if segment and segment.strip():
                    if re.match(separators, segment):
                        current_segment += segment
                        if current_segment.strip():
                            processed_segments.append(current_segment.strip())
                        current_segment = ""
                    else:
                        current_segment += segment

            # 处理最后一个片段
            if current_segment.strip():
                processed_segments.append(current_segment.strip())
                
        elif segmentation_type == 'linebreak':
            # 按换行符分割
            segments = text.split('\n')
            processed_segments = [seg.strip() for seg in segments if seg.strip()]
            
        elif segmentation_type == 'ai':
            # TODO: 实现AI分段逻辑
            processed_segments = [text]  # 临时返回整个文本作为一个段落
        
        # 创建分段记录
        segment_records = []
        
        for segment_text, is_new_paragraph in zip(processed_segments, is_new_paragraph_flags):
            if segment_text:
                try:
                    segment = MaterialSegment(
                        material_id=material_id,
                        original=segment_text,
                        translation="",
                        is_new_paragraph=is_new_paragraph  # 使用对应的标记
                    )
                    segment.save()
                    segment_records.append(segment)
                        
                except Exception as e:
                    print(f"Error creating segment: {str(e)}")
                    continue
                
        return segment_records

    @staticmethod
    def get_segments_by_material(material_id, page=1, per_page=20):
        """获取指定材料的所有分段"""
        skip = (page - 1) * per_page
        return MaterialSegment.objects(material_id=material_id).skip(skip).limit(per_page)

    @staticmethod
    def update_segment(segment_id, data):
        """更新分段信息"""
        segment = MaterialSegment.objects.get(id=segment_id)
        
        if 'translation' in data:
            segment.translation = data['translation']
        if 'grammar' in data:
            segment.grammar = data['grammar']
        if 'vocabulary' in data:
            vocabulary_items = []
            for item in data['vocabulary']:
                vocabulary_items.append(VocabularyItem(
                    word=item['word'],
                    reading=item.get('reading', ''),
                    meaning=item['meaning']
                ))
            segment.vocabulary = vocabulary_items
            
        segment.save()
        return segment

    @staticmethod
    def delete_segment(segment_id):
        """删除分段"""
        segment = MaterialSegment.objects.get(id=segment_id)
        segment.delete()
        return True