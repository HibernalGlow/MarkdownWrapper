"""
Markdown处理器基类
所有处理器都应该继承这个类并实现process方法
"""
import os
import logging
import shutil
from datetime import datetime

class BaseProcessor:
    """Markdown处理器基类"""
    
    def __init__(self, output_dir=None):
        """
        初始化处理器
        
        Args:
            output_dir: 输出目录路径，如果为None则使用默认的output目录
        """
        self.name = self.__class__.__name__
        
        # 如果没有指定输出目录，使用默认的output目录
        if output_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_dir = os.path.join(base_dir, 'output')
        
        self.output_dir = output_dir
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
    def process(self, input_path, **kwargs):
        """
        处理Markdown文件
        
        Args:
            input_path: 输入文件路径
            **kwargs: 其他参数
            
        Returns:
            str: 输出文件路径
        """
        raise NotImplementedError("子类必须实现process方法")
    
    def get_output_path(self, input_path, suffix=None):
        """
        根据输入路径生成输出路径
        
        Args:
            input_path: 输入文件路径
            suffix: 输出文件名后缀，如果为None则使用处理器名称
            
        Returns:
            str: 输出文件路径
        """
        # 获取原始文件名
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)
        
        # 如果没有指定后缀，使用处理器名称
        if suffix is None:
            suffix = self.name.lower()
        
        # 生成新的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{name}_{suffix}_{timestamp}{ext}"
        
        # 返回完整输出路径
        return os.path.join(self.output_dir, new_filename)
    
    def copy_file(self, input_path, output_path):
        """
        复制文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            shutil.copy2(input_path, output_path)
            return True
        except Exception as e:
            logging.error(f"复制文件失败: {str(e)}")
            return False
    
    def read_file(self, file_path):
        """
        读取文件内容
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 文件内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logging.error(f"读取文件失败: {str(e)}")
            return None
    
    def write_file(self, file_path, content):
        """
        写入文件内容
        
        Args:
            file_path: 文件路径
            content: 文件内容
            
        Returns:
            bool: 是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            logging.error(f"写入文件失败: {str(e)}")
            return False