#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
标题处理模块，处理Markdown文档中的标题格式化
支持独立运行和被其他模块导入使用
"""
import re
import sys
import argparse
import os
from pathlib import Path
import time
import cn2an
from datetime import datetime
from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.style import Style
from rich import print as rprint

def setup_logger(app_name="app", project_root=None):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        
    Returns:
        tuple: (logger, config_info)
            - logger: 配置好的 logger 实例
            - config_info: 包含日志配置信息的字典
    """
    # 获取项目根目录
    if project_root is None:
        project_root = Path(__file__).parent.resolve()
    
    # 清除默认处理器
    logger.remove()
    
    # 添加控制台处理器（简洁版格式）
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <blue>{elapsed}</blue> | <level>{level.icon} {level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
    )
    
    # 使用 datetime 构建日志路径
    current_time = datetime.now()
    date_str = current_time.strftime("%Y-%m-%d")
    hour_str = current_time.strftime("%H")
    minute_str = current_time.strftime("%M%S")
    
    # 构建日志目录和文件路径
    log_dir = os.path.join(project_root, "logs", app_name, date_str, hour_str)
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{minute_str}.log")
    
    # 添加文件处理器
    logger.add(
        log_file,
        level="DEBUG",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {elapsed} | {level.icon} {level: <8} | {name}:{function}:{line} - {message}",
    )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    return logger, config_info

logger, config_info = setup_logger(app_name="header_processor")

# 配置日志


class HeaderProcessor:
    """标题处理器，用于提取和处理Markdown文档中的标题"""
    
    def __init__(self):
        """初始化标题处理器"""
        # 移除代码保护器
        self.stats = {
            "processed_files": 0,
            "total_chars_processed": 0,
            "headers_processed": 0,
            "pattern_matches": {}
        }
    
    def convert_number(self, match, format_type):
        """
        通用的中文数字转换函数
        
        Args:
            match: 正则表达式匹配对象
            format_type: 格式类型
                'chapter': 章标题
                'section': 节标题
                'subsection': 子节标题
                'subsubsection': 小节标题
                'number_title': 数字标题
                'number_subtitle': 数字子标题
                
        Returns:
            str: 转换后的标题格式
        """
        try:
            # 处理数字标题的特殊情况
            if format_type in ['number_title', 'number_subtitle']:
                number = match.group(1)
                formats = {
                    'number_title': f'##### {number}. ',
                    'number_subtitle': f'###### {number}. '
                }
                result = formats.get(format_type)
                logger.info(f"转换数字标题成功: {match.group(0)} -> {result}")
                return result
                
            # 处理中文数字的情况
            chinese_num = match.group(1)
            # 检查是否是特殊字符
            special_chars = {'〇': '零', '两': '二'}
            if chinese_num in special_chars:
                chinese_num = special_chars[chinese_num]
                
            logger.debug(f"尝试转换数字: {chinese_num}")
            arabic_num = cn2an.cn2an(chinese_num, mode='smart')
            standard_chinese = cn2an.an2cn(arabic_num)
            
            formats = {
                'chapter': f'# 第{standard_chinese}章 ',
                'section': f'## 第{standard_chinese}节 ',
                'subsection': f'### {standard_chinese}、',
                'subsubsection': f'#### ({standard_chinese}) '
            }
            result = formats.get(format_type, match.group(0))
            logger.info(f"转换标题成功: {match.group(0)} -> {result}")
            return result
        except Exception as e:
            logger.error(f"转换标题失败: {match.group(0)}, 错误: {str(e)}")
            # 如果转换失败，保持原样
            return match.group(0)
    
    def extract_and_process_headers(self, text, header_levels=None):
        """
        提取并处理文档中的标题
        
        Args:
            text (str): 要处理的文本
            header_levels (list): 要处理的标题级别列表，例如[1,2,3,4,5,6]或[1,3,6]
                                如果为None，则默认处理所有标题级别(1-6)
        
        Returns:
            tuple: (处理后的文本, 提取的标题列表)
                标题列表格式为[(level, title, line_number), ...]
        """
        if header_levels is None:
            header_levels = [1, 2, 3, 4, 5, 6]
        
        logger.info(f"提取标题，处理级别: {header_levels}")
        
        lines = text.split('\n')
        headers = []
        
        for line_num, line in enumerate(lines):
            if line.startswith('#'):
                level = 0
                for char in line:
                    if (char == '#'):
                        level += 1
                    else:
                        break
                
                # 检查是否是有效的标题行(#后面有空格，且级别在指定范围内)
                if level > 0 and level <= 6 and len(line) > level and line[level] == ' ':
                    if level in header_levels:
                        header_text = line[level+1:].strip()
                        headers.append((level, header_text, line_num))
                        logger.debug(f"找到{level}级标题: {header_text}")
        
        logger.info(f"共提取了 {len(headers)} 个标题")
        self.stats["headers_processed"] += len(headers)
        
        return text, headers
    
    def process_headers_by_level(self, text, header_levels=None):
        """
        根据指定的标题级别处理文档中的标题格式化
        
        Args:
            text (str): 要处理的文本
            header_levels (list): 要处理的标题级别列表，例如[1,2,3,4,5,6]或[1,3,6]
                                如果为None，则默认处理所有标题级别(1-6)
        
        Returns:
            str: 处理后的文本
        """
        if header_levels is None:
            header_levels = [1, 2, 3, 4, 5, 6]
        
        logger.info(f"处理标题格式化，级别: {header_levels}")
        
        # 标题级别与相应的正则表达式映射
        header_patterns_by_level = {
            1: [(r'^第([一二三四五六七八九十百千万零两]+)章(?:\s*)', lambda m: self.convert_number(m, 'chapter'))],  # 一级标题: 章
            2: [(r'^第([一二三四五六七八九十百千万零两]+)节(?:\s*)', lambda m: self.convert_number(m, 'section'))],  # 二级标题: 节
            3: [(r'^([一二三四五六七八九十百千万零两]+)、(?:\s*)', lambda m: self.convert_number(m, 'subsection'))],  # 三级标题: 中文数字标题
            4: [(r'^\(([一二三四五六七八九十百千万零两]+)\)(?:\s*)', lambda m: self.convert_number(m, 'subsubsection'))],  # 四级标题: 带括号的中文数字标题
            5: [(r'^(\d+)\.(?:\s*)', lambda m: self.convert_number(m, 'number_title'))],  # 五级标题: 数字标题
            6: [(r'^(\d+\.\d+)\.(?:\s*)', lambda m: self.convert_number(m, 'number_subtitle'))]  # 六级标题: 数字子标题
        }
        
        # 根据选择的标题级别应用对应的正则表达式
        for level in header_levels:
            if level in header_patterns_by_level:
                for pattern, replacement in header_patterns_by_level[level]:
                    try:
                        prev_text = text
                        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
                        # 检查是否有变化
                        if prev_text != text:
                            pattern_name = f"Level{level}_{pattern[:20]}..." if isinstance(pattern, str) else f"Level{level}_函数替换"
                            self.stats["pattern_matches"][pattern_name] = self.stats["pattern_matches"].get(pattern_name, 0) + 1
                            logger.info(f"应用 {level} 级标题替换规则: {pattern}")
                    except Exception as e:
                        logger.error(f"应用 {level} 级标题替换规则失败: {pattern}, 错误: {str(e)}")
        
        return text
    
    def process_text(self, text, header_levels=None):
        """
        处理文本中的标题
        
        Args:
            text (str): 要处理的文本
            header_levels (list): 要处理的标题级别列表，默认为全部级别[1,2,3,4,5,6]
            
        Returns:
            dict: 包含处理结果和统计信息的字典
                {
                    "processed_text": 处理后的文本,
                    "headers": 提取的标题列表,
                    "stats": 处理统计信息
                }
        """
        if header_levels is None:
            header_levels = [1, 2, 3, 4, 5, 6]
            
        original_length = len(text)
        self.stats["total_chars_processed"] += original_length
        
        # 提取标题信息
        _, headers = self.extract_and_process_headers(text, header_levels)
        
        # 处理标题格式
        processed_text = self.process_headers_by_level(text, header_levels)
        
        # 增加处理文件计数
        self.stats["processed_files"] += 1
        
        return {
            "processed_text": processed_text,
            "headers": headers,
            "stats": self.stats
        }
    
    def process_file(self, file_path, header_levels=None, output_path=None):
        """
        处理单个文件
        
        Args:
            file_path (str): 要处理的文件路径
            header_levels (list): 要处理的标题级别列表，默认为全部级别[1,2,3,4,5,6]
            output_path (str): 输出文件路径，如果为None则覆盖原文件
            
        Returns:
            dict: 包含处理结果和统计信息的字典
        """
        logger.info(f"处理文件: {file_path}")
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # 处理文本
            result = self.process_text(text, header_levels)
            processed_text = result["processed_text"]
            
            # 确定输出路径
            if output_path is None:
                output_path = file_path
                
            # 写入处理后的内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_text)
                
            logger.info(f"处理完成，结果已写入: {output_path}")
            logger.info(f"处理后文本长度: {len(processed_text)} 字符")
            
            return result
            
        except Exception as e:
            logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
            return {
                "processed_text": text if 'text' in locals() else "",
                "headers": [],
                "stats": self.stats,
                "error": str(e)
            }
    
    def parse_header_levels(self, header_levels_input):
        """
        解析用户输入的标题级别
        
        Args:
            header_levels_input (str): 用户输入的标题级别，如"1,2,3"或"1-3"
            
        Returns:
            list: 要处理的标题级别列表
        """
        if not header_levels_input or header_levels_input.lower() == "all":
            return list(range(1, 7))  # 默认处理所有级别
            
        try:
            header_levels = []
            for part in header_levels_input.split(','):
                part = part.strip()
                if '-' in part:
                    # 处理范围，如"1-3"
                    start, end = map(int, part.split('-'))
                    header_levels.extend(range(start, end + 1))
                else:
                    # 处理单个数字
                    header_levels.append(int(part))
            
            # 确保标题级别在1-6的范围内
            header_levels = [level for level in header_levels if 1 <= level <= 6]
            # 去重并排序
            header_levels = sorted(set(header_levels))
            
            if not header_levels:
                logger.warning("无效的标题级别输入，使用默认值[1-6]")
                return list(range(1, 7))
            else:
                return header_levels
        except ValueError:
            logger.warning(f"无法解析输入 '{header_levels_input}'，使用默认值[1-6]")
            return list(range(1, 7))


def main():
    """主函数，当脚本独立运行时执行"""
    parser = argparse.ArgumentParser(description='Markdown 标题处理工具')
    parser.add_argument('--file', '-f', help='要处理的Markdown文件路径')
    parser.add_argument('--output', '-o', help='输出文件路径，默认覆盖原文件')
    parser.add_argument('--levels', '-l', default='1-6', 
                       help='要处理的标题级别，用逗号分隔，例如"1,2,3"或"1-3"，默认为"1-6"')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细日志')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logger.DEBUG)
    
    processor = HeaderProcessor()
    
    # 检查是否提供了输入文件
    if not args.file:
        # 从标准输入读取
        logger.info("从标准输入读取文本")
        text = sys.stdin.read()
        
        # 处理文本
        header_levels = processor.parse_header_levels(args.levels)
        result = processor.process_text(text, header_levels)
        
        # 输出到标准输出
        sys.stdout.write(result["processed_text"])
        
    else:
        # 检查文件是否存在
        if not os.path.isfile(args.file):
            logger.error(f"文件不存在: {args.file}")
            sys.exit(1)
        
        # 处理文件
        header_levels = processor.parse_header_levels(args.levels)
        result = processor.process_file(args.file, header_levels, args.output)
        
        # 输出统计信息
        logger.info("处理完成，统计信息:")
        logger.info(f"- 处理文件数: {result['stats']['processed_files']}")
        logger.info(f"- 处理字符数: {result['stats']['total_chars_processed']}")
        logger.info(f"- 处理标题数: {result['stats']['headers_processed']}")
        
        # 输出匹配规则统计
        if result['stats']['pattern_matches']:
            logger.info("标题匹配规则统计:")
            for pattern, count in sorted(result['stats']['pattern_matches'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"- {pattern}: {count}次")


if __name__ == '__main__':
    main()