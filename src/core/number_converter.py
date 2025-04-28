"""
数字转换模块，处理中文数字和阿拉伯数字的相互转换
"""
import cn2an
import logging
from src.core.base_processor import BaseProcessor
from src.core.code_protector import CodeProtectorProcessor
import re

class NumberConverterProcessor(BaseProcessor):
    """中文数字转换处理器"""
    
    def __init__(self, output_dir=None):
        """初始化处理器"""
        super().__init__(output_dir)
        self.code_protector = CodeProtectorProcessor(output_dir)
        
    def process(self, input_path, header_levels=None, **kwargs):
        """
        处理Markdown文件中的中文数字转换
        
        Args:
            input_path: 输入文件路径
            header_levels: 要处理的标题级别，默认为全部级别[1,2,3,4,5,6]
            **kwargs: 额外参数
                use_protector: 是否使用代码保护器，默认为True
                
        Returns:
            str: 输出文件路径
        """
        # 如果header_levels为None，处理所有级别
        if header_levels is None:
            header_levels = [1, 2, 3, 4, 5, 6]
            
        # 读取文件内容
        content = self.read_file(input_path)
        if content is None:
            return None
            
        use_protector = kwargs.get('use_protector', True)
        
        # 处理文本
        if use_protector:
            # 保护代码块
            protected_content = self.code_protector.protect_elements(content)
            
            # 处理标题格式化
            formatted_content = self._process_headers_by_level(protected_content, header_levels)
            
            # 恢复代码块
            content = self.code_protector.restore_elements(formatted_content)
        else:
            # 直接处理文本
            content = self._process_headers_by_level(content, header_levels)
        
        # 获取输出路径
        output_path = self.get_output_path(input_path)
        
        # 写入处理后的内容
        if self.write_file(output_path, content):
            logging.info(f"已处理中文数字: {output_path}")
            return output_path
        
        return None
    
    def _process_headers_by_level(self, text, header_levels):
        """
        根据指定的标题级别处理文档中的标题格式化
        
        Args:
            text: 要处理的文本
            header_levels: 要处理的标题级别列表
            
        Returns:
            str: 处理后的文本
        """
        logging.info(f"处理标题格式化，级别: {header_levels}")
        
        # 标题级别与相应的正则表达式映射
        header_patterns_by_level = {
            1: [(r'^第([一二三四五六七八九十百千万零两]+)章(?:\s*)', lambda m: self._convert_number(m, 'chapter'))],  # 一级标题: 章
            2: [(r'^第([一二三四五六七八九十百千万零两]+)节(?:\s*)', lambda m: self._convert_number(m, 'section'))],  # 二级标题: 节
            3: [(r'^([一二三四五六七八九十百千万零两]+)、(?:\s*)', lambda m: self._convert_number(m, 'subsection'))],  # 三级标题: 中文数字标题
            4: [(r'^\(([一二三四五六七八九十百千万零两]+)\)(?:\s*)', lambda m: self._convert_number(m, 'subsubsection'))],  # 四级标题: 带括号的中文数字标题
            5: [(r'^(\d+)\.(?:\s*)', lambda m: self._convert_number(m, 'number_title'))],  # 五级标题: 数字标题
            6: [(r'^(\d+\.\d+)\.(?:\s*)', lambda m: self._convert_number(m, 'number_subtitle'))]  # 六级标题: 数字子标题
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
                            logging.info(f"应用 {level} 级标题替换规则: {pattern_name}")
                    except Exception as e:
                        logging.error(f"应用 {level} 级标题替换规则失败: {pattern}, 错误: {str(e)}")
        
        return text
    
    def _convert_number(self, match, format_type):
        """
        通用的中文数字转换函数
        
        Args:
            match: 正则表达式匹配对象
            format_type: 格式类型
                'chapter': 章标题
                'section': 节标题
                'subsection': 子节标题
                'subsubsection': 小节标题
                'number_title': 数字标题
                'number_subtitle': 数字子标题
                
        Returns:
            str: 转换后的标题格式
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