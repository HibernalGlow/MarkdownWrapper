"""
代码块保护模块，用于在处理Markdown文件时保护代码块、行内代码和Markdown链接等不被修改
"""
import re
import logging
class CodeBlockProtector:
    """用于保护Markdown中的代码块、行内代码、链接和图片等不被格式化处理"""
    def __init__(self):
        # 代码块正则表达式
        self.code_block_pattern = re.compile(r'```[\s\S]*?```')
        self.inline_code_pattern = re.compile(r'`[^`]+`')
        # Markdown图片和链接
        self.md_image_pattern = re.compile(r'!\[(.*?)\]\((.*?)\)')
        self.md_link_pattern = re.compile(r'(?<!!)\[(.*?)\]\((.*?)\)')
        # 有序列表保护模式
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
            # logging.debug(f"保护代码块: {match.group(0)[:50]}...")
            return f'CODE_BLOCK_{len(self.code_blocks)-1}'
        
        # 保护行内代码
        def save_inline_code(match):
            self.inline_codes.append(match.group(0))
            # logging.debug(f"保护行内代码: {match.group(0)}")
            return f'INLINE_CODE_{len(self.inline_codes)-1}'
            
        # 保护 Markdown 图片
        def save_md_image(match):
            self.md_images.append(match.group(0))
            # logging.debug(f"保护Markdown图片: {match.group(0)[:50]}...")
            return f'MD_IMAGE_{len(self.md_images)-1}'
            
        # 保护 Markdown 链接
        def save_md_link(match):
            self.md_links.append(match.group(0))
            # logging.debug(f"保护Markdown链接: {match.group(0)[:50]}...")
            return f'MD_LINK_{len(self.md_links)-1}'
            
        # 保护有序列表
        def save_ordered_list(match):
            self.ordered_lists.append(match.group(0))
            # logging.debug(f"保护有序列表: {match.group(0)[:50]}...")
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