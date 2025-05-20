"""
基于marko的Markdown转换器基类
"""
import marko
import logging
from marko.renderer import Renderer
from marko.ext.gfm import GFM
import os
import re

class BaseMarkoTransformer(Renderer):
    """基础Markdown转换器，使用marko解析和转换Markdown文档"""
    
    def __init__(self):
        """初始化转换器"""
        super().__init__()
        self.parser = GFM()
        self.logger = logging.getLogger(self.__class__.__name__)

    def transform(self, markdown_text):
        """
        转换Markdown文本
        
        Args:
            markdown_text (str): 输入的Markdown文本
            
        Returns:
            str: 转换后的Markdown文本
        """
        # 解析Markdown文本为AST
        doc = self.parser.parse(markdown_text)
        
        # 遍历并转换AST
        return self.render(doc)
    
    def transform_file(self, file_path, output_path=None):
        """
        转换Markdown文件
        
        Args:
            file_path (str): 输入文件路径
            output_path (str, optional): 输出文件路径，默认覆盖输入文件
            
        Returns:
            str: 输出文件路径
        """
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 转换内容
            transformed_content = self.transform(content)
            
            # 确定输出路径
            if output_path is None:
                output_path = file_path
            
            # 写入文件
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(transformed_content)
            
            self.logger.info(f"已处理文件: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
            return None
    
    def _get_text_content(self, element):
        """获取元素的纯文本内容"""
        if hasattr(element, 'children'):
            if isinstance(element.children, list):
                return ''.join(self._get_text_content(child) for child in element.children)
            return str(element.children)
        return str(element)
