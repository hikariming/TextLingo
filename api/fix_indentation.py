#!/usr/bin/env python3
"""
修复user_service.py中的缩进问题
"""

import re

def fix_indentation_issues():
    file_path = "app/services/user_service.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复所有的缩进问题
    # 查找模式：if LoggingConfig.should_log_rls_debug():后面跟着缩进不正确的logger语句
    
    # 模式1: if语句后直接跟logger，需要增加缩进
    pattern1 = r'(\s+)if LoggingConfig\.should_log_rls_debug\(\):\s*\n(\s+)logger\.'
    def replace1(match):
        indent = match.group(1)
        logger_indent = match.group(2)
        # 确保logger的缩进比if语句多4个空格
        correct_logger_indent = indent + "    "
        return f'{indent}if LoggingConfig.should_log_rls_debug():\n{correct_logger_indent}logger.'
    
    content = re.sub(pattern1, replace1, content, flags=re.MULTILINE)
    
    # 修复额外的空格或错误缩进
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # 如果这一行是logger语句，且上一行是if LoggingConfig语句
        if i > 0 and 'logger.' in line and 'if LoggingConfig.should_log_rls_debug():' in lines[i-1]:
            # 获取上一行的缩进
            prev_line = lines[i-1]
            prev_indent = len(prev_line) - len(prev_line.lstrip())
            # logger应该比if多缩进4个空格
            correct_indent = ' ' * (prev_indent + 4)
            # 清理当前行的缩进并应用正确的缩进
            clean_line = line.lstrip()
            fixed_line = correct_indent + clean_line
            fixed_lines.append(fixed_line)
        else:
            fixed_lines.append(line)
    
    fixed_content = '\n'.join(fixed_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("✅ 缩进问题已修复")

if __name__ == "__main__":
    fix_indentation_issues()