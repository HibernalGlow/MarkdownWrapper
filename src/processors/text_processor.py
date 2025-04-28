"""
文本处理器模块，处理Markdown文本的格式化和内容替换
"""
import re
from src.utils.statistics import stats
from src.formatters.text_formatter import TextFormatter
from src.processors.table_processor import remove_empty_table_rows
from src.processors.header_processor import extract_and_process_headers, process_headers_by_level
import logging
# 正则表达式替换规则
patterns_and_replacements = [
    # 1. 基础格式清理
    (r'^ ',r''),  # 删除行首空格
    (r'(?:\r?\n){3,}', r'\n\n'),  # 将连续3个以上空行替换为两个空行
    (r'^.*?目\s{0,10}录.*$\n?', r''),  # 新增：修复"目 录"错误 spacing
    (r'^\d+\s{0,9}\n', r''),  # 删除行首数字和空格
    
    # 2. 中英文标点符号统一
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

def process_text(text, header_levels=None):
    """处理文本的核心函数"""
    logging.info("开始处理文本")
    formatter = TextFormatter()
    
    try:
        # 先进行基础文本格式化
        logging.info("进行基础文本格式化")
        text = formatter.format_text(text)
        stats.increment_format_changes()
        
        # 提取和处理标题
        text, headers = extract_and_process_headers(text, header_levels)
        if headers:
            logging.info(f"成功提取{len(headers)}个标题")
        
        # 处理表格空行和重复行
        logging.info("处理表格空行和重复行")
        text = remove_empty_table_rows(text)
        text = formatter.format_text(text)
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
                        stats.add_pattern_match(pattern_name)
                else:
                    prev_text = text
                    text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
                    if prev_text != text:
                        pattern_name = pattern if isinstance(pattern, str) else "函数替换"
                        stats.add_pattern_match(pattern_name)
                # logging.debug(f"成功应用替换规则: {pattern}")
            except Exception as e:
                logging.error(f"应用替换规则失败: {pattern}, 错误: {str(e)}")
                continue
        
        # 根据用户选择的标题级别处理标题格式化
        text = process_headers_by_level(text, header_levels)
        
        # 更新处理字符数统计
        stats.add_chars_processed(len(text))
        
        logging.info("文本处理完成")
        return text
    except Exception as e:
        logging.error(f"处理文本时发生错误: {str(e)}")
        return text  # 返回原文本