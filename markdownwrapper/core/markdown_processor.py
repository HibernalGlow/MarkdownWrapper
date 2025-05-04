"""
Markdown处理器模块，集成所有处理功能，提供完整的Markdown处理流程
"""
import os
import re
import logging
from markdownwrapper.core.base_processor import BaseProcessor
from markdownwrapper.core.code_protector import CodeProtectorProcessor
from markdownwrapper.core.text_formatter import TextFormatterProcessor
from markdownwrapper.core.table_processor import TableProcessor
from markdownwrapper.core.number_converter import NumberConverterProcessor

class MarkdownProcessor(BaseProcessor):
    """统一的Markdown处理器，集成所有处理功能"""
    
    def __init__(self, output_dir=None):
        """初始化处理器"""
        super().__init__(output_dir)
        self.code_protector = CodeProtectorProcessor(output_dir)
        self.text_formatter = TextFormatterProcessor(output_dir)
        self.table_processor = TableProcessor(output_dir)
        self.number_converter = NumberConverterProcessor(output_dir)
        
        # 标准替换规则
        self.patterns_and_replacements = [
            # 1. 基础格式清理
            (r'^ ',r''),  # 删除行首空格
            (r'(?:\r?\n){3,}', r'\n\n'),  # 将连续3个以上空行替换为两个空行
            (r'^.*?目\s{0,10}录.*$\n?', r''),  # 修复"目 录"错误 spacing
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
    
    def process(self, input_path, header_levels=None, **kwargs):
        """
        处理Markdown文件，应用所有处理功能
        
        Args:
            input_path: 输入文件路径
            header_levels: 要处理的标题级别，默认为全部级别[1,2,3,4,5,6]
            **kwargs: 额外参数
                skip_steps: 要跳过的处理步骤列表，可选值包括:
                    'format': 跳过文本格式化
                    'table': 跳过表格处理
                    'header': 跳过标题处理
                    'pattern': 跳过模式替换
                
        Returns:
            str: 输出文件路径
        """
        # 如果header_levels为None，处理所有级别
        if header_levels is None:
            header_levels = [1, 2, 3, 4, 5, 6]
            
        skip_steps = kwargs.get('skip_steps', [])
            
        # 读取文件内容
        content = self.read_file(input_path)
        if content is None:
            return None
        
        # 获取中间处理文件路径
        temp_path = self.get_output_path(input_path, suffix="temp")
        
        # 写入中间处理文件
        if not self.write_file(temp_path, content):
            return None
            
        # 当前处理路径
        current_path = temp_path
        output_path = None
        
        # 1. 调用代码保护器
        protected_path = self.code_protector.process(current_path)
        if protected_path:
            current_path = protected_path
            
            # 2. 处理表格
            if 'table' not in skip_steps:
                table_path = self.table_processor.process(current_path, use_protector=False)
                if table_path:
                    current_path = table_path
            
            # 3. 文本格式化
            if 'format' not in skip_steps:
                format_path = self.text_formatter.process(current_path, use_protector=False)
                if format_path:
                    current_path = format_path
                    
            # 4. 处理标题
            if 'header' not in skip_steps and header_levels:
                header_path = self.number_converter.process(current_path, header_levels=header_levels, use_protector=False)
                if header_path:
                    current_path = header_path
                    
            # 5. 应用标准替换规则
            if 'pattern' not in skip_steps:
                pattern_path = self._apply_patterns(current_path)
                if pattern_path:
                    current_path = pattern_path
                    
            # 6. 恢复代码
            output_path = self.code_protector.restore_process(current_path)
            
        # 如果处理失败，返回原始文件
        if not output_path:
            logging.error("处理失败，返回原始文件")
            return input_path
            
        # 清理中间文件
        self._cleanup_temp_files(temp_path)
            
        return output_path
    
    def _apply_patterns(self, input_path):
        """
        应用标准替换规则
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            str: 输出文件路径
        """
        # 读取文件内容
        content = self.read_file(input_path)
        if content is None:
            return None
            
        # 应用替换规则
        for pattern, replacement in self.patterns_and_replacements:
            try:
                prev_content = content
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
                # 检查是否有变化
                if prev_content != content:
                    pattern_name = pattern if isinstance(pattern, str) and len(pattern) < 30 else "复杂正则表达式"
                    logging.debug(f"应用替换规则: {pattern_name}")
            except Exception as e:
                logging.error(f"应用替换规则失败: {pattern}, 错误: {str(e)}")
                
        # 获取输出路径
        output_path = self.get_output_path(input_path, suffix="patterns")
        
        # 写入处理后的内容
        if self.write_file(output_path, content):
            logging.info(f"已应用标准替换规则: {output_path}")
            return output_path
        
        return None
    
    def _cleanup_temp_files(self, base_path):
        """
        清理处理过程中生成的中间文件
        
        Args:
            base_path: 基础文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取目录和文件名
            directory = os.path.dirname(base_path)
            filename = os.path.basename(base_path)
            name, ext = os.path.splitext(filename)
            
            # 移除temp_前缀
            if "temp_" in name:
                base_name = name.replace("temp_", "")
            else:
                base_name = name
                
            # 查找匹配的临时文件
            for file in os.listdir(directory):
                if file.startswith(base_name) and "_temp_" in file and file.endswith(ext):
                    file_path = os.path.join(directory, file)
                    try:
                        os.remove(file_path)
                        logging.debug(f"已删除临时文件: {file_path}")
                    except Exception as e:
                        logging.error(f"删除临时文件失败: {file_path}, 错误: {str(e)}")
            
            return True
        except Exception as e:
            logging.error(f"清理临时文件失败: {str(e)}")
            return False