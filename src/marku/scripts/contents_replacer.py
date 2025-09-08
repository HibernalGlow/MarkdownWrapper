import re
import cn2an
import pangu
import logging
import os
import sys
import argparse
import time
from datetime import datetime
from colorama import init, Fore, Style
from rich.prompt import Prompt, Confirm  # 导入rich提示模块


# 初始化 colorama
init()


# 设置日志
# logging, config_info = setup_logging({
#     'script_name': 'contents_replacer',
#     'console_enabled': True
# })

# 添加统计变量

stats = {
    "processed_files": 0,
    "total_chars_processed": 0,
    "format_changes": 0,
    "pattern_matches": {}
}

class CodeBlockProtector:
    def __init__(self):
        self.code_block_pattern = re.compile(r'```[\s\S]*?```')
        self.inline_code_pattern = re.compile(r'`[^`]+`')
        # 添加新的正则表达式匹配 Markdown 图片和链接
        self.md_image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
        self.md_link_pattern = re.compile(r'(?<!!)\[(.*?)\]\((.*?)\)')
        # 添加有序列表保护模式，匹配连续的数字编号列表项
        self.ordered_list_pattern = re.compile(r'(?:^\d+\.\s+.*?$\n)+', re.MULTILINE)
    
    def protect_codes(self, text):
        """保护代码块、行内代码和Markdown链接"""
        self.code_blocks = []
        self.inline_codes = []
        self.md_images = []
        self.md_links = []
        self.ordered_lists = []  # 新增有序列表保存列表
        
        # 保护代码块
        def save_code_block(match):
            self.code_blocks.append(match.group(0))
            logging.debug(f"保护代码块: {match.group(0)[:50]}...")
            return f'CODE_BLOCK_{len(self.code_blocks)-1}'
        
        # 保护行内代码
        def save_inline_code(match):
            self.inline_codes.append(match.group(0))
            logging.debug(f"保护行内代码: {match.group(0)}")
            return f'INLINE_CODE_{len(self.inline_codes)-1}'
            
        # 保护 Markdown 图片
        def save_md_image(match):
            self.md_images.append(match.group(0))
            logging.debug(f"保护Markdown图片: {match.group(0)[:50]}...")
            return f'MD_IMAGE_{len(self.md_images)-1}'
            
        # 保护 Markdown 链接
        def save_md_link(match):
            self.md_links.append(match.group(0))
            logging.debug(f"保护Markdown链接: {match.group(0)[:50]}...")
            return f'MD_LINK_{len(self.md_links)-1}'
            
        # 保护有序列表
        def save_ordered_list(match):
            self.ordered_lists.append(match.group(0))
            logging.debug(f"保护有序列表: {match.group(0)[:50]}...")
            return f'ORDERED_LIST_{len(self.ordered_lists)-1}'
        
        # 顺序很重要：先保护代码块，再保护行内代码，然后保护链接，最后保护有序列表
        text = self.code_block_pattern.sub(save_code_block, text)
        text = self.inline_code_pattern.sub(save_inline_code, text)
        text = self.md_image_pattern.sub(save_md_image, text)
        text = self.md_link_pattern.sub(save_md_link, text)
        text = self.ordered_list_pattern.sub(save_ordered_list, text)
        return text
    
    def restore_codes(self, text):
        """恢复代码块、行内代码和Markdown链接"""
        # 恢复顺序与保护顺序相反
        for i, ordered_list in enumerate(self.ordered_lists):
            text = text.replace(f'ORDERED_LIST_{i}', ordered_list)
            
        for i, link in enumerate(self.md_links):
            text = text.replace(f'MD_LINK_{i}', link)
            
        for i, image in enumerate(self.md_images):
            text = text.replace(f'MD_IMAGE_{i}', image)
        
        for i, code in enumerate(self.inline_codes):
            text = text.replace(f'INLINE_CODE_{i}', code)
        
        for i, block in enumerate(self.code_blocks):
            text = text.replace(f'CODE_BLOCK_{i}', block)
        
        return text
class TextFormatter:
    def __init__(self):
        self.code_protector = CodeBlockProtector()
    
    def format_text(self, text):
        """格式化文本：处理中英文间距、标点符号等"""
        # 保护代码块
        # text = self.code_protector.protect_codes(text)
        
        # 使用 pangu 处理中英文格式
        # text = pangu.spacing_text(text)  # 自动处理中英文间距
        
        # 处理全角字符转半角
        # text = self.full_to_half(text)
        
        # # 处理连续标题问题
        # text = self.handle_consecutive_headers(text)
        
        # 恢复代码块
        # text = self.code_protector.restore_codes(text)
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

# 定义你的文件路径
import os
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, '1.md')

def convert_number(match, format_type):
    """
    通用的中文数字转换函数
    format_type: 
        'chapter': 章标题
        'section': 节标题
        'subsection': 子节标题
        'subsubsection': 小节标题
        'number_title': 数字标题
        'number_subtitle': 数字子标题
    """
    try:
        # 处理数字标题的特殊情况
        if format_type in ['number_title', 'number_subtitle']:
            number = match.group(1)
            formats = {
                'number_title': f'##### {number}. ',
                'number_subtitle': f'###### {number}. '
            }
            result = formats.get(format_type)
            logging.info(f"转换数字标题成功: {match.group(0)} -> {result}")
            return result
            
        # 处理中文数字的情况
        chinese_num = match.group(1)
        # 检查是否是特殊字符
        special_chars = {'〇': '零', '两': '二'}
        if chinese_num in special_chars:
            chinese_num = special_chars[chinese_num]
            
        logging.debug(f"尝试转换数字: {chinese_num}")
        arabic_num = cn2an.cn2an(chinese_num, mode='smart')
        standard_chinese = cn2an.an2cn(arabic_num)
        
        formats = {
            'chapter': f'# 第{standard_chinese}章 ',
            'section': f'## 第{standard_chinese}节 ',
            'subsection': f'### {standard_chinese}、',
            'subsubsection': f'#### ({standard_chinese}) '
        }
        result = formats.get(format_type, match.group(0))
        logging.info(f"转换标题成功: {match.group(0)} -> {result}")
        return result
    except Exception as e:
        logging.error(f"转换标题失败: {match.group(0)}, 错误: {str(e)}")
        # 如果转换失败，保持原样
        return match.group(0)

# 修改patterns_and_replacements，移除标题格式化相关正则
patterns_and_replacements = [
    # 1. 基础格式清理
    (r'^ ',r''),  # 删除行首空格
    (r'(?:\r?\n){3,}', r'\n\n'),  # 将连续3个以上空行替换为两个空行
    (r'^.*?目\s{0,10}录.*$\n?', r''),  # 新增：修复"目 录"错误 spacing
    
    # 2. 中英文标点符号统一 (注意: 标题格式化正则已移至process_headers_by_level函数)
    (r'\（', r'('),  # 中文括号转英文
    (r'\）', r')'),
    (r'\「', r'['),  # 中文引号转方括号
    (r'\」', r']'),
    (r'\【', r'['),  # 中文方括号转英文
    (r'\】', r']'),
    (r'\．', r'.'),  # 中文点号转英文
    (r'\。', r'.'),  # 句号转点号
    (r'\，', r', '),  # 中文逗号转英文
    (r'\；', r'; '),  # 中文分号转英文
    (r'\：', r': '),  # 中文冒号转英文
    (r'\！', r'!'),  # 中文感叹号转英文
    (r'\？', r'?'),  # 中文问号转英文
    (r'\"\"|\"', r'"'),  # 中文引号转英文
    (r'\'\'|\'', r"'"),
    
    # 3. 表格格式优化
    (r'([^|])\n\|(.*?\|.*?\|.*?\n)',r'\1\n\n|\2'),  # 在表格前文字后添加换行
    (r'\|\n([^|])',r'|\n\n\1'),  # 表格最后一行后添加空行
    (r':(-{1,1000}):',r'\1'),  # 修复表格分割线重复问题
    
    # 4. HTML标签清理
    (r'</body></html> ',r''),  # 删除HTML结束标签
    (r'<html><body>',r''),  # 删除HTML开始标签
    
    # 5. 数学符号和特殊字符处理
    (r'\$\\rightarrow\$',r'→'),  # LaTeX箭头转Unicode
    (r'\$\\leftarrow\$',r'←'),
    (r'\$=\$',r'='),  # LaTeX等号转普通等号
    (r'\^',r'+'),  # 处理上标符号
    (r'\$\+\$',r'+'),  # LaTeX加号转普通加号
    (r'\^\+',r'+'),
    (r'\$\\mathrm\{([a-z])\}\$',r'\1'),  # 简化LaTeX数学模式文本
    
    # 6. 代码和标记格式化
    (r'^\[([\u4e00-\u9fa5A-Za-z0-9]+)\]',r'`[\1]`'),  # 将方括号内容转为代码格式
]

def remove_empty_table_rows(text):
    """处理表格中的连续空行和首尾空行"""
    lines = text.split('\n')
    result = []
    table_lines = []
    in_table = False
    
    for line in lines:
        # 检查是否是表格行
        if '|' in line:
            if not in_table:
                in_table = True
            table_lines.append(line)
        else:
            if in_table:
                # 处理表格结束
                processed_table = process_table(table_lines)
                result.extend(processed_table)
                table_lines = []
                in_table = False
            result.append(line)
    
    # 处理文件末尾的表格
    if table_lines:
        processed_table = process_table(table_lines)
        result.extend(processed_table)
    
    return '\n'.join(result)

def process_table(table_lines):
    """处理单个表格的行"""
    if not table_lines:
        return []
    
    original_length = len(table_lines)
    logging.info(f"开始处理表格，原始行数: {original_length}")
    
    # 移除首尾的空行
    while table_lines and is_empty_table_row(table_lines[0]):
        logging.debug("移除表格首部空行")
        table_lines.pop(0)
    while table_lines and is_empty_table_row(table_lines[-1]):
        logging.debug("移除表格尾部空行")
        table_lines.pop()
    
    # 处理中间的连续空行和重复行
    result = []
    prev_line = None
    prev_empty = False
    removed_empty = 0
    removed_duplicate = 0
    
    for line in table_lines:
        # 处理空行
        if is_empty_table_row(line):
            if not prev_empty:
                result.append(line)
                prev_empty = True
            else:
                removed_empty += 1
                logging.debug("移除连续空行")
            continue
        
        # 处理重复行
        if line == prev_line:
            removed_duplicate += 1
            logging.debug(f"移除重复行: {line}")
            continue
        
        result.append(line)
        prev_line = line
        prev_empty = False
    
    logging.info(f"表格处理完成: 移除了 {removed_empty} 个连续空行, {removed_duplicate} 个重复行")
    logging.info(f"表格行数变化: {original_length} -> {len(result)}")
    return result

def is_empty_table_row(line):
    """检查是否是空的表格行"""
    if not line.strip():
        return True
    parts = line.split('|')[1:-1]  # 去掉首尾的|
    return all(cell.strip() == '' for cell in parts)


def extract_and_process_headers(text, header_levels=None):
    """
    提取并处理文档中的标题
    
    Args:
        text (str): 要处理的文本
        header_levels (list): 要处理的标题级别列表，例如[1,2,3,4,5,6]或[1,3,6]
                            如果为None，则默认处理所有标题级别(1-6)
    
    Returns:
        str: 处理后的文本
        list: 提取的标题列表，格式为[(level, title, line_number), ...]
    """
    if header_levels is None:
        header_levels = [1, 2, 3, 4, 5, 6]
    
    logging.info(f"提取标题，处理级别: {header_levels}")
    
    lines = text.split('\n')
    headers = []
    
    for line_num, line in enumerate(lines):
        if line.startswith('#'):
            level = 0
            for char in line:
                if char == '#':
                    level += 1
                else:
                    break
            
            # 检查是否是有效的标题行(#后面有空格，且级别在指定范围内)
            if level > 0 and level <= 6 and len(line) > level and line[level] == ' ':
                if level in header_levels:
                    header_text = line[level+1:].strip()
                    headers.append((level, header_text, line_num))
                    logging.debug(f"找到{level}级标题: {header_text}")
    
    logging.info(f"共提取了 {len(headers)} 个标题")
    return text, headers

def process_headers_by_level(text, header_levels=None):
    """
    根据指定的标题级别处理文档中的标题格式化
    
    Args:
        text (str): 要处理的文本
        header_levels (list): 要处理的标题级别列表，例如[1,2,3,4,5,6]或[1,3,6]
                            如果为None，则默认处理所有标题级别(1-6)
    
    Returns:
        str: 处理后的文本
    """
    if header_levels is None:
        header_levels = [1, 2, 3, 4, 5, 6]
    
    logging.info(f"处理标题格式化，级别: {header_levels}")
    
    # 标题级别与相应的正则表达式映射
    header_patterns_by_level = {
        1: [(r'^第([一二三四五六七八九十百千万零两]+)章(?:\s*)', lambda m: convert_number(m, 'chapter'))],  # 一级标题: 章
        2: [(r'^第([一二三四五六七八九十百千万零两]+)节(?:\s*)', lambda m: convert_number(m, 'section'))],  # 二级标题: 节
        3: [(r'^([一二三四五六七八九十百千万零两]+)、(?:\s*)', lambda m: convert_number(m, 'subsection'))],  # 三级标题: 中文数字标题
        4: [(r'^\(([一二三四五六七八九十百千万零两]+)\)(?:\s*)', lambda m: convert_number(m, 'subsubsection'))],  # 四级标题: 带括号的中文数字标题
        5: [(r'^(\d+)\.(?:\s*)', lambda m: convert_number(m, 'number_title'))],  # 五级标题: 数字标题
        6: [(r'^(\d+\.\d+)\.(?:\s*)', lambda m: convert_number(m, 'number_subtitle'))]  # 六级标题: 数字子标题
    }
    
    # 根据选择的标题级别应用对应的正则表达式
    for level in header_levels:
        if level in header_patterns_by_level:
            for pattern, replacement in header_patterns_by_level[level]:
                try:
                    prev_text = text
                    text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
                    # 检查是否有变化
                    if prev_text != text:
                        pattern_name = f"Level{level}_{pattern[:20]}..." if isinstance(pattern, str) else f"Level{level}_函数替换"
                        stats["pattern_matches"][pattern_name] = stats["pattern_matches"].get(pattern_name, 0) + 1
                        logging.info(f"应用 {level} 级标题替换规则: {pattern}")
                except Exception as e:
                    logging.error(f"应用 {level} 级标题替换规则失败: {pattern}, 错误: {str(e)}")
    
    return text

def process_text(text, patterns_and_replacements):
    """处理文本的核心函数"""
    logging.info("开始处理文本")
    formatter = TextFormatter()
    
    try:
        # 询问用户要处理哪几级标题
        try:
            header_levels_input = Prompt.ask(
                "请输入要处理的标题级别(多个级别用逗号分隔，如1,2,3，默认处理所有标题级别1-6)", 
                default="1-6"
            )
            
            # 解析用户输入的标题级别
            if header_levels_input:
                try:
                    header_levels = []
                    for part in header_levels_input.split(','):
                        part = part.strip()
                        if '-' in part:
                            # 处理范围，如"1-3"
                            start, end = map(int, part.split('-'))
                            header_levels.extend(range(start, end + 1))
                        else:
                            # 处理单个数字
                            header_levels.append(int(part))
                    
                    # 确保标题级别在1-6的范围内
                    header_levels = [level for level in header_levels if 1 <= level <= 6]
                    # 去重并排序
                    header_levels = sorted(set(header_levels))
                    
                    if not header_levels:
                        header_levels = [1, 2, 3, 4, 5, 6]
                        logging.warning("无效的标题级别输入，使用默认值[1-6]")
                    else:
                        logging.info(f"将处理标题级别: {header_levels}")
                except ValueError:
                    header_levels = [1, 2, 3, 4, 5, 6]
                    logging.warning(f"无法解析输入 '{header_levels_input}'，使用默认值[1-6]")
            else:
                header_levels = [1, 2, 3, 4, 5, 6]
        except Exception as e:
            header_levels = [1, 2, 3, 4, 5, 6]
            logging.error(f"询问标题级别时出错: {str(e)}，使用默认值[1-6]")
        
        # 先进行基础文本格式化
        logging.info("进行基础文本格式化")
        text = formatter.format_text(text)
        stats["format_changes"] += 1
        
        # 提取和处理标题
        text, headers = extract_and_process_headers(text, header_levels)
        if headers:
            logging.info(f"成功提取{len(headers)}个标题")
            # 这里可以添加更多对标题的处理逻辑
        
        # 处理表格空行和重复行
        logging.info("处理表格空行和重复行")
        text = remove_empty_table_rows(text)
        
        # 再应用其他替换规则
        logging.info("应用替换规则")
        for pattern, replacement in patterns_and_replacements:
            try:
                if callable(replacement):
                    # 记录替换前的文本
                    prev_text = text
                    text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
                    # 检查是否有变化
                    if prev_text != text:
                        pattern_name = pattern if isinstance(pattern, str) else "函数替换"
                        stats["pattern_matches"][pattern_name] = stats["pattern_matches"].get(pattern_name, 0) + 1
                else:
                    prev_text = text
                    text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
                    if prev_text != text:
                        pattern_name = pattern if isinstance(pattern, str) else "函数替换"
                        stats["pattern_matches"][pattern_name] = stats["pattern_matches"].get(pattern_name, 0) + 1
                logging.debug(f"成功应用替换规则: {pattern}")
            except Exception as e:
                logging.error(f"应用替换规则失败: {pattern}, 错误: {str(e)}")
                continue
        
        # 根据用户选择的标题级别处理标题格式化
        text = process_headers_by_level(text, header_levels)
        
        logging.info("文本处理完成")
        return text
    except Exception as e:
        logging.error(f"处理文本时发生错误: {str(e)}")
        return text  # 返回原文本

def process_file(file_path):
    """处理单个文件"""
    try:
        print(f"{Fore.CYAN}处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        original_length = len(text)
        logging.info(f"成功读取文件，字符数: {original_length}")
        
        # 处理文本
        start_time = time.time()
        processed_text = process_text(text, patterns_and_replacements)
        end_time = time.time()
        
        # 更新统计
        stats["processed_files"] += 1
        stats["total_chars_processed"] += original_length
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(processed_text)
        
        new_length = len(processed_text)
        char_diff = new_length - original_length
        diff_str = f"{char_diff:+d}" if char_diff != 0 else "0"
        
        print(f"{Fore.GREEN}完成: {os.path.basename(file_path)} ")
        print(f"  - 处理耗时: {end_time - start_time:.2f}秒")
        print(f"  - 文件大小: {original_length} → {new_length} ({diff_str}字符)")
        print(f"  - 应用规则: {sum(stats['pattern_matches'].values())}次匹配{Style.RESET_ALL}")
        
        return True
    except Exception as e:
        logging.error(f"处理文件失败: {file_path}", exc_info=True)
        print(f"{Fore.RED}处理失败: {str(e)}{Style.RESET_ALL}")
        return False

def process_directory(directory_path):
    """处理目录中的所有 Markdown 文件"""
    print(f"{Fore.CYAN}扫描目录: {directory_path}{Style.RESET_ALL}")
    md_files = []
    
    # 查找所有 Markdown 文件
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    if not md_files:
        print(f"{Fore.YELLOW}警告: 目录中没有找到 Markdown 文件{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}找到 {len(md_files)} 个 Markdown 文件待处理{Style.RESET_ALL}")
    
    # 处理每个文件
    for i, file_path in enumerate(md_files):
        print(f"\n{Fore.CYAN}[{i+1}/{len(md_files)}] 处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        process_file(file_path)
    
    # 显示总结
    print(f"\n{Fore.GREEN}===== 处理完成 ====={Style.RESET_ALL}")
    print(f"处理文件数: {stats['processed_files']}")
    print(f"处理字符数: {stats['total_chars_processed']}")
    print(f"格式化次数: {stats['format_changes']}")
    
    # 显示各种模式的匹配次数
    if stats["pattern_matches"]:
        print(f"\n{Fore.CYAN}替换规则统计:{Style.RESET_ALL}")
        for pattern, count in sorted(stats["pattern_matches"].items(), key=lambda x: x[1], reverse=True):
            if isinstance(pattern, str) and len(pattern) > 50:
                pattern_display = pattern[:47] + "..."
            else:
                pattern_display = pattern
            print(f"  - {pattern_display}: {count}次")

def main():
    parser = argparse.ArgumentParser(description='Markdown 文件格式化工具')
    parser.add_argument('--path', help='要处理的文件或目录路径')
    parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理目录')
    args = parser.parse_args()
    
    try:
        # 获取处理路径
        path = None
        if args.clipboard:
            import pyperclip
            path = pyperclip.paste().strip().strip('"')
            if not os.path.exists(path):
                print(f"{Fore.RED}剪贴板中的路径无效: {path}{Style.RESET_ALL}")
                return
            print(f"{Fore.GREEN}从剪贴板读取路径: {path}{Style.RESET_ALL}")
        elif args.path:
            path = args.path
            if not os.path.exists(path):
                print(f"{Fore.RED}路径无效: {path}{Style.RESET_ALL}")
                return
        else:
            # 使用默认路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(current_dir, '1.md')
            if not os.path.exists(path):
                print(f"{Fore.YELLOW}默认文件不存在: {path}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}将使用当前目录: {current_dir}{Style.RESET_ALL}")
                path = current_dir
        
        # 处理文件或目录
        if os.path.isfile(path):
            process_file(path)
        elif os.path.isdir(path):
            if args.recursive:
                process_directory(path)
            else:
                # 只处理目录下的MD文件，不递归
                md_files = [os.path.join(path, f) for f in os.listdir(path) 
                           if f.lower().endswith('.md') and os.path.isfile(os.path.join(path, f))]
                
                if not md_files:
                    print(f"{Fore.YELLOW}警告: 目录中没有找到 Markdown 文件{Style.RESET_ALL}")
                    return
                
                print(f"{Fore.GREEN}找到 {len(md_files)} 个 Markdown 文件待处理{Style.RESET_ALL}")
                
                for i, file_path in enumerate(md_files):
                    print(f"\n{Fore.CYAN}[{i+1}/{len(md_files)}] 处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
                    process_file(file_path)
                
                # 显示总结
                print(f"\n{Fore.GREEN}===== 处理完成 ====={Style.RESET_ALL}")
                print(f"处理文件数: {stats['processed_files']}")
                print(f"处理字符数: {stats['total_chars_processed']}")
        
    except Exception as e:
        logging.error(f"主程序执行失败: {str(e)}", exc_info=True)
        print(f"{Fore.RED}执行失败: {str(e)}{Style.RESET_ALL}")

if __name__ == '__main__':
    print(f"{Fore.CYAN}===== Markdown 格式化工具（记得处理标题和目录） ====={Style.RESET_ALL}")
    main()