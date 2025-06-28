import mistune  
from mistune.renderers.markdown import MarkdownRenderer  
from typing import Dict, Any, List  
  
class ConsecutiveHeaderRenderer(MarkdownRenderer):  
    def __init__(self, min_consecutive_headers=2, max_blank_lines=1,   
                 levels_to_process=None, processing_mode=1):  
        super().__init__()  
        self.min_consecutive_headers = min_consecutive_headers  
        self.max_blank_lines = max_blank_lines  
        self.levels_to_process = set(levels_to_process or range(1, 7))  
        self.processing_mode = processing_mode  
        self.consecutive_headers = []  
        self.blank_line_count = 0  
          
    def heading(self, token: Dict[str, Any], state) -> str:  
        level = token["attrs"]["level"]  
        if level in self.levels_to_process:  
            # 处理连续标题逻辑  
            return self._process_consecutive_heading(token, state)  
        return super().heading(token, state)