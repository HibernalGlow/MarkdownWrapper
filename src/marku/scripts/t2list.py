import re
import pyperclip
from loguru import logger
import os
import sys
from pathlib import Path
from datetime import datetime
import time

def setup_logger(app_name="app", project_root=None, console_output=True):
    """配置 Loguru 日志系统
    
    Args:
        app_name: 应用名称，用于日志目录
        project_root: 项目根目录，默认为当前文件所在目录
        console_output: 是否输出到控制台，默认为True
        
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
    
    # 有条件地添加控制台处理器（简洁版格式）
    if console_output:
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
        enqueue=True,     )
    
    # 创建配置信息字典
    config_info = {
        'log_file': log_file,
        'log_dir': log_dir,
        'project_root': project_root,
    }
    
    logger.info(f"日志系统已初始化，应用名称: {app_name}")
    logger.debug(f"日志文件路径: {log_file}")
    return logger, config_info

# 初始化日志系统
logger, config_info = setup_logger(app_name="t2list", console_output=False)

def convert_headings_to_list(text):
    """将Markdown标题转换为带缩进的有序列表
    
    Args:
        text: 输入的Markdown文本
        
    Returns:
        str: 转换后的文本
    """
    start_time = time.time()
    logger.info("开始转换标题为列表")
    logger.debug(f"输入文本长度: {len(text)} 字符")
    
    try:
        if not text:
            logger.warning("输入文本为空")
            return ""
        
        lines = text.splitlines()
        logger.debug(f"总行数: {len(lines)}")
        
        result = []
        counters = [0] * 6  # 每个级别的计数器
        level_stack = []    # 用于跟踪标题层级
        current_indent = 0  # 当前缩进级别
        in_list = False     # 是否在处理列表
        list_block = []     # 当前列表块
        content_indent = 0  # 内容的缩进级别（标题缩进+1）
        
        # 统计信息
        processed_headings = 0
        processed_lists = 0
        empty_lines = 0
        other_lines = 0
        
        for line_num, line in enumerate(lines, 1):
            try:
                heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                list_match = re.match(r'^(\s*)((?:\d+\.|\*|\-)\s+)(.+)$', line)
                
                if line_num % 100 == 0:  # 每100行记录一次进度
                    logger.debug(f"处理进度: {line_num}/{len(lines)} 行")
                
                # 处理标题
                if heading_match:
                    processed_headings += 1
                    # 如果有未处理的列表，先处理它
                    if list_block:
                        logger.debug(f"在处理标题前，先完成 {len(list_block)} 行列表内容")
                        result.extend(list_block)
                        list_block = []
                        in_list = False
                    
                    level = len(heading_match.group(1))
                    content = heading_match.group(2)
                    
                    logger.debug(f"第{line_num}行: 找到 H{level} 标题: {content[:30]}{'...' if len(content) > 30 else ''}")
                    
                    # 更新层级栈
                    while level_stack and level_stack[-1] >= level:
                        level_stack.pop()
                    level_stack.append(level)
                    
                    # 计算标题缩进
                    current_indent = len(level_stack) - 1
                    # 内容缩进比标题多一级
                    content_indent = current_indent + 1
                    
                    logger.debug(f"标题层级栈: {level_stack}, 当前缩进: {current_indent}")
                    
                    # 更新计数器
                    counters[current_indent] += 1
                    for i in range(current_indent + 1, 6):
                        counters[i] = 0
                        
                    # 生成标题行
                    indent = "    " * current_indent
                    number = str(counters[current_indent]) + "."
                    
                    if '**' in content:
                        formatted_line = f"{indent}{number} {content}"
                    else:
                        formatted_line = f"{indent}{number} **{content}**"
                    
                    result.append(formatted_line)
                    logger.debug(f"生成标题行: {formatted_line}")
                    
                # 处理列表
                elif list_match or (in_list and line.strip() and line.startswith('    ')):
                    if not in_list:
                        in_list = True
                        list_block = []
                        processed_lists += 1
                        logger.debug(f"第{line_num}行: 开始处理新的列表块")
                    
                    # 列表项在内容缩进级别的基础上保持原有的相对缩进
                    base_indent = "    " * content_indent
                    extra_indent = " " * (len(line) - len(line.lstrip()))
                    formatted_line = base_indent + extra_indent + line.lstrip()
                    list_block.append(formatted_line)
                    
                # 处理空行
                elif not line.strip():
                    empty_lines += 1
                    if list_block:
                        logger.debug(f"第{line_num}行: 遇到空行，完成当前列表块 ({len(list_block)} 行)")
                        result.extend(list_block)
                        list_block = []
                        in_list = False
                    result.append(line)
                    
                # 处理其他行
                else:
                    other_lines += 1
                    if list_block:
                        logger.debug(f"第{line_num}行: 遇到其他内容，完成当前列表块 ({len(list_block)} 行)")
                        result.extend(list_block)
                        list_block = []
                        in_list = False
                    # 其他内容也使用内容缩进级别
                    formatted_line = "    " * content_indent + line
                    result.append(formatted_line)
                    
            except Exception as line_error:
                logger.error(f"处理第{line_num}行时出错: {line_error}")
                logger.debug(f"问题行内容: {line}")
                # 出错时保持原行不变
                result.append(line)
                continue
        
        # 处理最后的列表块
        if list_block:
            logger.debug(f"处理最终剩余的列表块 ({len(list_block)} 行)")
            result.extend(list_block)
        
        # 记录统计信息和性能
        elapsed_time = time.time() - start_time
        logger.info(f"转换完成 - 标题: {processed_headings}, 列表块: {processed_lists}, 空行: {empty_lines}, 其他行: {other_lines}")
        logger.info(f"输出结果总行数: {len(result)}")
        logger.info(f"处理耗时: {elapsed_time:.3f}秒")
        logger.info(f"平均每行处理时间: {elapsed_time/len(lines)*1000:.2f}毫秒")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"转换过程中出现错误: {str(e)}")
        logger.exception("详细错误信息:")
        raise

def main():
    """主函数：从剪贴板读取内容，转换后写回剪贴板"""
    program_start_time = time.time()
    
    try:
        logger.info("=== t2list 程序启动 ===")
        logger.info(f"日志配置: {config_info}")
        
        # 获取剪贴板内容
        logger.info("正在读取剪贴板内容...")
        clipboard_start_time = time.time()
        clipboard_text = pyperclip.paste()
        clipboard_read_time = time.time() - clipboard_start_time
        
        logger.debug(f"剪贴板读取耗时: {clipboard_read_time:.3f}秒")
        
        if not clipboard_text:
            logger.warning("剪贴板内容为空，程序退出")
            return
        
        # 分析输入内容
        lines_count = len(clipboard_text.splitlines())
        heading_count = len(re.findall(r'^#{1,6}\s+', clipboard_text, re.MULTILINE))
        
        logger.info(f"成功读取剪贴板内容:")
        logger.info(f"  - 总字符数: {len(clipboard_text)}")
        logger.info(f"  - 总行数: {lines_count}")
        logger.info(f"  - 标题数量: {heading_count}")

        # 转换内容
        logger.info("开始转换标题为列表...")
        convert_start_time = time.time()
        converted_text = convert_headings_to_list(clipboard_text)
        convert_time = time.time() - convert_start_time
        
        logger.info(f"转换耗时: {convert_time:.3f}秒")

        # 写回剪贴板
        logger.info("正在将转换结果写入剪贴板...")
        copy_start_time = time.time()
        pyperclip.copy(converted_text)
        copy_time = time.time() - copy_start_time
        
        logger.debug(f"剪贴板写入耗时: {copy_time:.3f}秒")
        logger.info("转换完成，结果已复制到剪贴板")
        
        # 总结性能信息
        total_time = time.time() - program_start_time
        logger.info(f"程序总耗时: {total_time:.3f}秒")
        
    except pyperclip.PyperclipException as clipboard_error:
        logger.error(f"剪贴板操作失败: {str(clipboard_error)}")
        logger.info("可能原因: 没有安装剪贴板依赖或系统不支持剪贴板操作")
        raise
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        logger.exception("详细错误信息:")
        raise
    finally:
        final_time = time.time() - program_start_time
        logger.info(f"=== t2list 程序结束，总运行时间: {final_time:.3f}秒 ===")

if __name__ == "__main__":
    main()
