"""
代码保护器模块，用于处理Markdown文档中的代码块、行内代码、链接等特殊结构
"""
import re
import logging
from src.core.base_processor import BaseProcessor

class CodeProtectorProcessor(BaseProcessor):
    """代码块保护器处理器"""
    
    def __init__(self, output_dir=None):
        """初始化处理器"""
        super().__init__(output_dir)
        self.code_block_pattern = re.compile(r'```[\s\S]*?```')
        self.inline_code_pattern = re.compile(r'`[^`]+`')
        # 添加新的正则表达式匹配 Markdown 图片和链接
        self.md_image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
        self.md_link_pattern = re.compile(r'(?<!!)\[(.*?)\]\((.*?)\)')
        # 添加有序列表保护模式，匹配连续的数字编号列表项
        self.ordered_list_pattern = re.compile(r'(?:^\d+\.\s+.*?$\n)+', re.MULTILINE)
        
        # 存储保护的内容
        self.protected_elements = {
            'code_blocks': [],
            'inline_codes': [],
            'md_images': [],
            'md_links': [],
            'ordered_lists': []
        }
    
    def process(self, input_path, **kwargs):
        """
        处理Markdown文件，保护代码块等特殊结构
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            str: 输出文件路径，包含处理后的内容
        """
        # 读取文件内容
        content = self.read_file(input_path)
        if content is None:
            return None
        
        # 保护特殊结构
        protected_content = self.protect_elements(content)
        
        # 获取输出路径
        output_path = self.get_output_path(input_path)
        
        # 写入处理后的内容
        if self.write_file(output_path, protected_content):
            logging.info(f"已保护文件特殊结构: {output_path}")
            return output_path
        
        return None
    
    def restore_process(self, input_path, **kwargs):
        """
        恢复之前保护的特殊结构
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            str: 输出文件路径，包含恢复后的内容
        """
        # 读取文件内容
        content = self.read_file(input_path)
        if content is None:
            return None
        
        # 恢复特殊结构
        restored_content = self.restore_elements(content)
        
        # 获取输出路径
        output_path = self.get_output_path(input_path, suffix="restored")
        
        # 写入处理后的内容
        if self.write_file(output_path, restored_content):
            logging.info(f"已恢复文件特殊结构: {output_path}")
            return output_path
        
        return None
    
    def protect_elements(self, text):
        """
        保护文本中的特殊结构
        
        Args:
            text: 原始文本
            
        Returns:
            str: 处理后的文本，特殊结构被替换为占位符
        """
        # 重置保护的内容
        self.protected_elements = {
            'code_blocks': [],
            'inline_codes': [],
            'md_images': [],
            'md_links': [],
            'ordered_lists': []
        }
        
        # 保护代码块
        def save_code_block(match):
            self.protected_elements['code_blocks'].append(match.group(0))
            logging.debug(f"保护代码块: {match.group(0)[:50]}...")
            return f'CODE_BLOCK_{len(self.protected_elements["code_blocks"])-1}'
        
        # 保护行内代码
        def save_inline_code(match):
            self.protected_elements['inline_codes'].append(match.group(0))
            logging.debug(f"保护行内代码: {match.group(0)}")
            return f'INLINE_CODE_{len(self.protected_elements["inline_codes"])-1}'
            
        # 保护 Markdown 图片
        def save_md_image(match):
            self.protected_elements['md_images'].append(match.group(0))
            logging.debug(f"保护Markdown图片: {match.group(0)[:50]}...")
            return f'MD_IMAGE_{len(self.protected_elements["md_images"])-1}'
            
        # 保护 Markdown 链接
        def save_md_link(match):
            self.protected_elements['md_links'].append(match.group(0))
            logging.debug(f"保护Markdown链接: {match.group(0)[:50]}...")
            return f'MD_LINK_{len(self.protected_elements["md_links"])-1}'
            
        # 保护有序列表
        def save_ordered_list(match):
            self.protected_elements['ordered_lists'].append(match.group(0))
            logging.debug(f"保护有序列表: {match.group(0)[:50]}...")
            return f'ORDERED_LIST_{len(self.protected_elements["ordered_lists"])-1}'
        
        # 顺序很重要：先保护代码块，再保护行内代码，然后保护链接，最后保护有序列表
        text = self.code_block_pattern.sub(save_code_block, text)
        text = self.inline_code_pattern.sub(save_inline_code, text)
        text = self.md_image_pattern.sub(save_md_image, text)
        text = self.md_link_pattern.sub(save_md_link, text)
        text = self.ordered_list_pattern.sub(save_ordered_list, text)
        
        # 记录保护的元素数量
        for key, value in self.protected_elements.items():
            if value:
                logging.info(f"保护了 {len(value)} 个 {key}")
                
        return text
    
    def restore_elements(self, text):
        """
        恢复文本中被保护的特殊结构
        
        Args:
            text: 包含占位符的文本
            
        Returns:
            str: 恢复后的文本
        """
        # 恢复顺序与保护顺序相反
        for i, ordered_list in enumerate(self.protected_elements['ordered_lists']):
            text = text.replace(f'ORDERED_LIST_{i}', ordered_list)
            
        for i, link in enumerate(self.protected_elements['md_links']):
            text = text.replace(f'MD_LINK_{i}', link)
            
        for i, image in enumerate(self.protected_elements['md_images']):
            text = text.replace(f'MD_IMAGE_{i}', image)
        
        for i, code in enumerate(self.protected_elements['inline_codes']):
            text = text.replace(f'INLINE_CODE_{i}', code)
        
        for i, block in enumerate(self.protected_elements['code_blocks']):
            text = text.replace(f'CODE_BLOCK_{i}', block)
        
        return text