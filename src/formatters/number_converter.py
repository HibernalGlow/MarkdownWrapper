"""
数字转换模块，处理中文数字和阿拉伯数字的相互转换
"""
import cn2an
from src.utils.statistics import stats
import logging

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
            # logging.info(f"转换数字标题成功: {match.group(0)} -> {result}")
            return result
            
        # 处理中文数字的情况
        chinese_num = match.group(1)
        # 检查是否是特殊字符
        special_chars = {'〇': '零', '两': '二'}
        if chinese_num in special_chars:
            chinese_num = special_chars[chinese_num]
            
        # logging.debug(f"尝试转换数字: {chinese_num}")
        arabic_num = cn2an.cn2an(chinese_num, mode='smart')
        standard_chinese = cn2an.an2cn(arabic_num)
        
        formats = {
            'chapter': f'# 第{standard_chinese}章 ',
            'section': f'## 第{standard_chinese}节 ',
            'subsection': f'### {standard_chinese}、',
            'subsubsection': f'#### ({standard_chinese}) '
        }
        result = formats.get(format_type, match.group(0))
        # logging.info(f"转换标题成功: {match.group(0)} -> {result}")
        return result
    except Exception as e:
        logging.error(f"转换标题失败: {match.group(0)}, 错误: {str(e)}")
        # 如果转换失败，保持原样
        return match.group(0)