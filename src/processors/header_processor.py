"""
标题处理器模块，用于提取和处理Markdown文档中的标题
"""
import re
from ..utils.logger import logger
from ..utils.statistics import stats
from ..formatters.number_converter import convert_number

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
    
    logger.info(f"提取标题，处理级别: {header_levels}")
    
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
                    logger.debug(f"找到{level}级标题: {header_text}")
    
    logger.info(f"共提取了 {len(headers)} 个标题")
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
    
    logger.info(f"处理标题格式化，级别: {header_levels}")
    
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
                        stats.add_pattern_match(pattern_name)
                        # logger.info(f"应用 {level} 级标题替换规则: {pattern}")
                except Exception as e:
                    logger.error(f"应用 {level} 级标题替换规则失败: {pattern}, 错误: {str(e)}")
    
    return text