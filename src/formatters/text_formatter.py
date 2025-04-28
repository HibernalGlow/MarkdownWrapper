"""
文本格式化模块，用于处理Markdown文本中的格式问题
"""
import re
import pangu
from src.formatters.code_protector import CodeBlockProtector
import logging
class TextFormatter:
    """文本格式化类，用于格式化Markdown文档"""
    def __init__(self):
        self.code_protector = CodeBlockProtector()
    
    def format_text(self, text):
        """格式化文本：处理中英文间距、标点符号等"""
        # 保护代码块
        text = self.code_protector.protect_codes(text)
        
        # 使用 pangu 处理中英文格式
        text = pangu.spacing_text(text)  # 自动处理中英文间距
        
        # 处理全角字符转半角
        text = self.full_to_half(text)
        
        # 处理连续标题问题
        text = self.handle_consecutive_headers(text)
        
        # 恢复代码块
        text = self.code_protector.restore_codes(text)
        return text

    def handle_consecutive_headers(self, text):
        """处理连续的同级标题，将连续3个以上的同级标题转为普通文本"""
        # 处理多行中的连续标题
        lines = text.split('\n')
        result_lines = []
        
        # 多行标题处理
        current_level = None
        consecutive_headers = []
        
        for line in lines:
            # 检查是否是标题行(以#开头)
            if line.startswith('#'):
                # 计算#号数量
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                        
                # 只处理2-6级标题
                if 2 <= level <= 6 and len(line) > level and line[level] == ' ':
                    content = line[level+1:]  # 标题内容(跳过#和空格)
                    
                    if level == current_level:
                        consecutive_headers.append((line, content))
                    else:
                        # 处理之前收集的连续标题
                        if len(consecutive_headers) >= 3:
                            # 保留前两个标题
                            result_lines.extend([h[0] for h in consecutive_headers[:2]])
                            # 后面的只保留内容
                            result_lines.extend([h[1] for h in consecutive_headers[2:]])
                            logging.info(f"转换了 {len(consecutive_headers)-2} 个连续的 {current_level} 级标题为普通文本")
                        else:
                            # 不足3个，全部保留
                            result_lines.extend([h[0] for h in consecutive_headers])
                        
                        # 重置收集器
                        current_level = level
                        consecutive_headers = [(line, content)]
                else:
                    # 不是有效的标题行，视为普通文本
                    if len(consecutive_headers) >= 2:
                        result_lines.extend([h[0] for h in consecutive_headers[:2]])
                        result_lines.extend([h[1] for h in consecutive_headers[2:]])
                        logging.info(f"转换了 {len(consecutive_headers)-2} 个连续的 {current_level} 级标题为普通文本")
                    else:
                        result_lines.extend([h[0] for h in consecutive_headers])
                    
                    result_lines.append(line)
                    current_level = None
                    consecutive_headers = []
            else:
                # 不是标题行，处理之前积累的标题
                if len(consecutive_headers) >= 2:
                    result_lines.extend([h[0] for h in consecutive_headers[:2]])
                    result_lines.extend([h[1] for h in consecutive_headers[2:]])
                    logging.info(f"转换了 {len(consecutive_headers)-2} 个连续的 {current_level} 级标题为普通文本")
                else:
                    result_lines.extend([h[0] for h in consecutive_headers])
                
                # 添加当前非标题行
                result_lines.append(line)
                current_level = None
                consecutive_headers = []
        
        # 处理文档末尾可能剩余的连续标题
        if len(consecutive_headers) >= 3:
            result_lines.extend([h[0] for h in consecutive_headers[:2]])
            result_lines.extend([h[1] for h in consecutive_headers[2:]])
            logging.info(f"转换了 {len(consecutive_headers)-2} 个连续的 {current_level} 级标题为普通文本")
        else:
            result_lines.extend([h[0] for h in consecutive_headers])
        
        # 处理单行中的连续标题
        processed_text = '\n'.join(result_lines)
        
        # 收集需要处理的行和位置信息
        lines_to_process = []  # 存储需要处理的行和位置信息
        
        for line_number, line in enumerate(processed_text.split('\n')):
            # 查找行内的所有标题位置
            header_positions = []  # 存储标题位置
            header_levels = []     # 存储标题级别
            i = 0
            
            while i < len(line):
                # 检查是否可能是标题标记(至少2个#)
                if i < len(line) - 1 and line[i] == '#' and line[i+1] == '#':
                    start = i
                    level = 0
                    
                    # 计算连续的#号数量
                    while i < len(line) and line[i] == '#':
                        level += 1
                        i += 1
                    
                    # 标题后面必须有空格
                    if i < len(line) and line[i] == ' ' and 2 <= level <= 6:
                        header_positions.append((start, i+1))  # 保存标题标记的起始和结束位置(包括空格)
                        header_levels.append(level)
                        continue
                i += 1
            
            # 如果发现至少3个同级标题，添加到处理列表
            if len(header_positions) >= 3:
                # 检查是否是同级标题
                first_level = header_levels[0]
                if all(level == first_level for level in header_levels):
                    lines_to_process.append((line_number, line, header_positions, first_level))
        
        # 处理需要修改的行
        if lines_to_process:
            result_lines = processed_text.split('\n')
            
            for line_number, line, positions, level in lines_to_process:
                logging.info(f"处理行 {line_number+1} 中的 {len(positions)} 个连续 {level} 级标题")
                
                # 保持前两个标题不变，修改后续标题
                new_line = line
                
                # 从后往前处理，避免修改位置影响
                for i in range(len(positions)-1, 1, -1):
                    start, end = positions[i]
                    # 替换第三个及之后的标题标记（包括后面的空格）
                    new_line = new_line[:start] + new_line[end:]
                
                result_lines[line_number] = new_line
                logging.info("处理单行连续标题，移除了标题标记")
            
            processed_text = '\n'.join(result_lines)
        
        logging.info(f"处理完成，文本长度: {len(processed_text)}")
        return processed_text

    def full_to_half(self, text):
        """全角转半角"""
        full_half_map = {
            # '：': ':',
            # '；': ';',
            # '，': ',',
            # '。': '.',
            # '！': '!',
            # '？': '?',
            '（': '(',
            '）': ')',
            '［': '[',
            '］': ']',
            '【': '[',
            '】': ']',
            '｛': '{',
            '｝': '}',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '｜': '|',
            '＼': '\\',
            '／': '/',
            # '《': '<',
            # '》': '>',
            '％': '%',
            '＃': '#',
            '＆': '&',
            '＊': '*',
            '＠': '@',
            '＾': '^',
            '～': '~',
            '｀': '`',
            ' 、':'、'
        }
        for full, half in full_half_map.items():
            text = text.replace(full, half)
        return text