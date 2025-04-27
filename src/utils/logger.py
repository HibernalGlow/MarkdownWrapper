"""
日志模块
"""
import logging
from colorama import init, Fore, Style
from nodes.record.logger_config import setup_logger

# 初始化 colorama
init()

def get_logger():
    """设置和获取日志记录器"""
    logger, config_info = setup_logger({
        'script_name': 'contents_replacer',
        'console_enabled': True
    })
    return logger

# 全局日志实例
logger = get_logger()