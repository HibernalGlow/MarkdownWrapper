"""
标题转换器 - 使用marko库实现标题识别与转换
"""
import re
import logging
import cn2an
from marko.renderer import Renderer
from marko.block import Heading, Paragraph

class HeaderTransformer(Renderer):
    """
    标题转换器: 识别特定模式的文本并将其转换为标题
    利用marko的块解析功能，直接操作文档对象
    """
    
    def __init__(self, header_levels=None):
        """
        初始化标题转换器
        
        Args:
            header_levels (list, optional): 要处理的标题级别列表，如[1,2,3,4,5,6]
        """
        super().__init__()
        # 如果没有指定标题级别，默认处理所有级别
        self.header_levels = header_levels or [1, 2, 3, 4, 5, 6]
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 定义标题模式
        self.title_patterns = {
            1: re.compile(r'^第([一二三四五六七八九十百千万零两]+)章(?:\s*)(.*)$'),  # 第X章
            2: re.compile(r'^第([一二三四五六七八九十百千万零两]+)节(?:\s*)(.*)$'),  # 第X节
            3: re.compile(r'^([一二三四五六七八九十百千万零两]+)、(?:\s*)(.*)$'),    # X、
            4: re.compile(r'^\(([一二三四五六七八九十百千万零两]+)\)(?:\s*)(.*)$'),  # (X)
            5: re.compile(r'^(\d+)\.(?:\s*)(.*)$'),                               # 数字.
            6: re.compile(r'^(\d+\.\d+)\.(?:\s*)(.*)$')                           # 数字.数字.
        }

    def render_paragraph(self, element):
        """
        处理段落元素，检查是否符合标题格式
        
        Args:
            element: marko段落元素
        
        Returns:
            str: 处理后的文本
        """
        # 仅处理指定级别的标题
        for level in self.header_levels:
            if level not in self.title_patterns:
                continue
            
            # 获取段落文本
            text = ''.join(self.render_children(element))
            
            # 尝试匹配标题模式
            match = self.title_patterns[level].match(text)
            if match:
                number = match.group(1)
                content = match.group(2) if len(match.groups()) > 1 else ""
                
                # 转换标题
                try:
                    # 处理中文数字的情况
                    if level in [1, 2, 3, 4]:
                        # 转换中文数字
                        try:
                            # 检查特殊字符
                            special_chars = {'〇': '零', '两': '二'}
                            if number in special_chars:
                                number = special_chars[number]
                                
                            # 转换为阿拉伯数字再转回中文，确保标准化
                            arabic_num = cn2an.cn2an(number, mode='smart')
                            standard_chinese = cn2an.an2cn(arabic_num)
                            
                            # 生成对应级别的标题
                            if level == 1:
                                result = f"# 第{standard_chinese}章 {content}"
                            elif level == 2:
                                result = f"## 第{standard_chinese}节 {content}"
                            elif level == 3:
                                result = f"### {standard_chinese}、{content}"
                            elif level == 4:
                                result = f"#### ({standard_chinese}) {content}"
                            
                            self.logger.info(f"转换标题: {text} -> {result}")
                            return result
                        except Exception as e:
                            self.logger.error(f"中文数字转换失败: {text}, 错误: {str(e)}")
                            return super().render_paragraph(element)
                    else:
                        # 处理数字标题的特殊情况
                        if level == 5:
                            result = f"##### {number}. {content}"
                        elif level == 6:
                            result = f"###### {number}. {content}"
                        
                        self.logger.info(f"转换数字标题: {text} -> {result}")
                        return result
                except Exception as e:
                    self.logger.error(f"标题转换失败: {text}, 错误: {str(e)}")
        
        # 如果不是标题，则保持原样
        return super().render_paragraph(element)
    
    def render_document(self, element):
        """渲染整个文档"""
        return ''.join(self.render_children(element))
