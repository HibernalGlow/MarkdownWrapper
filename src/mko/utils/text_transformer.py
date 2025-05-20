"""
文本格式化转换器：处理文本格式化，如标点符号转换，中英文间距等
"""
from mko.utils.marko_transformer import BaseMarkoTransformer
import re
import pangu
import logging

class TextTransformer(BaseMarkoTransformer):
    """文本格式化转换器：处理各种文本格式问题"""
    
    def __init__(self):
        """初始化文本格式化转换器"""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 标点替换映射
        self.punctuation_map = {
            '（': '(',
            '）': ')',
            '［': '[',
            '］': ']',
            '【': '[',
            '】': ']',
            '｛': '{',
            '｝': '}',
            '．': '.',
            '。': '.',
            '，': ', ',
            '；': '; ',
            '：': ': ',
            '！': '!',
            '？': '?',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '｜': '|',
            '＼': '\\',
            '／': '/',
            '％': '%',
            '＃': '#',
            '＆': '&',
            '＊': '*',
            '＠': '@',
            '＾': '^',
            '～': '~',
            '｀': '`'
        }
    
    def transform(self, markdown_text):
        """
        转换Markdown文本，处理格式化问题
        
        Args:
            markdown_text (str): 输入的Markdown文本
            
        Returns:
            str: 转换后的Markdown文本
        """
        # 使用pangu处理中英文间距
        text = pangu.spacing_text(markdown_text)
        
        # 标点符号转换
        for cn_punct, en_punct in self.punctuation_map.items():
            text = text.replace(cn_punct, en_punct)
        
        # 处理连续空行
        text = re.sub(r'(?:\r?\n){3,}', r'\n\n', text)
        
        # 处理行首空格
        text = re.sub(r'(?m)^ +', '', text)
        
        # 删除"目录"行
        text = re.sub(r'^.*?目\s{0,10}录.*$\n?', '', text, flags=re.MULTILINE)
        
        # HTML标签清理
        text = text.replace('</body></html> ', '').replace('<html><body>', '')
        
        # 使用marko进行其他处理
        return super().transform(text)
    
    def render_paragraph(self, element):
        """处理段落元素的格式化"""
        # 获取段落文本
        text = super().render_paragraph(element)
        
        # 进一步处理段落文本（如果需要）
        return text
    
    def render_text(self, element):
        """处理文本元素的格式化"""
        text = str(element.children)
        
        # 处理LaTeX数学符号
        text = text.replace('$\\rightarrow$', '→')
        text = text.replace('$\\leftarrow$', '←')
        text = text.replace('$=$', '=')
        text = text.replace('$+$', '+')
        text = re.sub(r'\$\\mathrm\{([a-z])\}\$', r'\1', text)
        
        # 处理上标符号
        text = text.replace('^', '+')
        text = text.replace('^+', '+')
        
        return text
