"""
表格处理器模块，用于处理Markdown文档中的表格格式化
"""
import logging
from markdownwrapper.core.base_processor import BaseProcessor
from markdownwrapper.core.code_protector import CodeProtectorProcessor

class TableProcessor(BaseProcessor):
    """表格处理器，用于处理Markdown表格格式"""
    
    def __init__(self, output_dir=None):
        """初始化处理器"""
        super().__init__(output_dir)
        self.code_protector = CodeProtectorProcessor(output_dir)
    
    def process(self, input_path, **kwargs):
        """
        处理Markdown文件中的表格格式
        
        Args:
            input_path: 输入文件路径
            **kwargs: 额外参数
                use_protector: 是否使用代码保护器，默认为True
                
        Returns:
            str: 输出文件路径
        """
        # 读取文件内容
        content = self.read_file(input_path)
        if content is None:
            return None
            
        use_protector = kwargs.get('use_protector', True)
        
        # 处理文本
        if use_protector:
            # 保护代码块
            protected_content = self.code_protector.protect_elements(content)
            
            # 处理表格
            formatted_content = self._remove_empty_table_rows(protected_content)
            
            # 恢复代码块
            content = self.code_protector.restore_elements(formatted_content)
        else:
            # 直接处理文本
            content = self._remove_empty_table_rows(content)
        
        # 获取输出路径
        output_path = self.get_output_path(input_path)
        
        # 写入处理后的内容
        if self.write_file(output_path, content):
            logging.info(f"已处理表格: {output_path}")
            return output_path
        
        return None
    
    def _remove_empty_table_rows(self, text):
        """
        处理表格中的连续空行和首尾空行
        
        Args:
            text: 要处理的文本
            
        Returns:
            str: 处理后的文本
        """
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
                    processed_table = self._process_table(table_lines)
                    result.extend(processed_table)
                    table_lines = []
                    in_table = False
                result.append(line)
        
        # 处理文件末尾的表格
        if table_lines:
            processed_table = self._process_table(table_lines)
            result.extend(processed_table)
        
        return '\n'.join(result)
    
    def _process_table(self, table_lines):
        """
        处理单个表格的行
        
        Args:
            table_lines: 表格的行列表
            
        Returns:
            list: 处理后的表格行列表
        """
        if not table_lines:
            return []
        
        original_length = len(table_lines)
        logging.info(f"开始处理表格，原始行数: {original_length}")
        
        # 移除首尾的空行
        while table_lines and self._is_empty_table_row(table_lines[0]):
            logging.debug("移除表格首部空行")
            table_lines.pop(0)
        while table_lines and self._is_empty_table_row(table_lines[-1]):
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
            if self._is_empty_table_row(line):
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
    
    def _is_empty_table_row(self, line):
        """
        检查是否是空的表格行
        
        Args:
            line: 要检查的行
            
        Returns:
            bool: 是否是空的表格行
        """
        if not line.strip():
            return True
        parts = line.split('|')[1:-1]  # 去掉首尾的|
        return all(cell.strip() == '' for cell in parts)