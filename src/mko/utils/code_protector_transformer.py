"""
代码块保护转换器：确保代码块不被其他转换器修改
"""
from mko.utils.marko_transformer import BaseMarkoTransformer
from marko.block import CodeBlock, FencedCode
from marko.inline import CodeSpan
import logging

class CodeProtectorTransformer(BaseMarkoTransformer):
    """代码块保护转换器：保留代码块原始格式"""
    
    def __init__(self):
        """初始化代码保护转换器"""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.code_blocks = {}
        self.inline_codes = {}
        self.placeholder_counter = 0
    
    def transform(self, markdown_text):
        """
        处理Markdown文本，保护代码块
        
        Args:
            markdown_text (str): 输入的Markdown文本
            
        Returns:
            str: 转换后的Markdown文本
        """
        # 重置存储
        self.code_blocks = {}
        self.inline_codes = {}
        self.placeholder_counter = 0
        
        # 解析Markdown文本
        doc = self.parser.parse(markdown_text)
        
        # 保护代码块和行内代码
        protected_text = self.render(doc)
        
        return protected_text
    
    def restore_code_blocks(self, markdown_text):
        """
        恢复被保护的代码块
        
        Args:
            markdown_text (str): 包含代码块占位符的Markdown文本
            
        Returns:
            str: 恢复代码块后的Markdown文本
        """
        text = markdown_text
        
        # 恢复代码块
        for placeholder, code_block in self.code_blocks.items():
            text = text.replace(placeholder, code_block)
        
        # 恢复行内代码
        for placeholder, inline_code in self.inline_codes.items():
            text = text.replace(placeholder, inline_code)
        
        return text
    
    def render_fenced_code(self, element):
        """保护围栏代码块"""
        # 生成代码块Markdown
        lang = element.lang or ""
        code = element.children
        code_block = f"```{lang}\n{code}\n```"
        
        # 创建占位符
        placeholder = f"CODE_BLOCK_{self.placeholder_counter}"
        self.placeholder_counter += 1
        
        # 存储代码块
        self.code_blocks[placeholder] = code_block
        self.logger.debug(f"保护代码块: {placeholder}")
        
        # 返回占位符
        return placeholder
    
    def render_code_block(self, element):
        """保护缩进代码块"""
        # 生成代码块Markdown
        code = element.children
        lines = code.split('\n')
        indented_lines = ['    ' + line for line in lines]
        code_block = '\n'.join(indented_lines)
        
        # 创建占位符
        placeholder = f"CODE_BLOCK_{self.placeholder_counter}"
        self.placeholder_counter += 1
        
        # 存储代码块
        self.code_blocks[placeholder] = code_block
        self.logger.debug(f"保护缩进代码块: {placeholder}")
        
        # 返回占位符
        return placeholder
    
    def render_code_span(self, element):
        """保护行内代码"""
        # 生成行内代码Markdown
        code = element.children
        inline_code = f"`{code}`"
        
        # 创建占位符
        placeholder = f"INLINE_CODE_{self.placeholder_counter}"
        self.placeholder_counter += 1
        
        # 存储行内代码
        self.inline_codes[placeholder] = inline_code
        self.logger.debug(f"保护行内代码: {placeholder}")
        
        # 返回占位符
        return placeholder
