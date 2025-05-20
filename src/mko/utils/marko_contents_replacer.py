"""
Markdown内容转换主程序，使用marko库处理Markdown文档
"""
import argparse
import os
import sys
import logging
import time
from datetime import datetime
import colorama
from colorama import Fore, Style
from rich.prompt import Prompt, Confirm

# 导入各种转换器
from mko.utils.code_protector_transformer import CodeProtectorTransformer
from markdownwrapper.core.header_transformer import HeaderTransformer
from mko.utils.text_transformer import TextTransformer
from mko.utils.table_transformer import TableTransformer

# 初始化colorama
colorama.init()

# 设置日志
def setup_logging():
    """设置日志配置"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建文件处理器
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"marko_transformer_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# 统计信息
stats = {
    "processed_files": 0,
    "total_chars_processed": 0,
    "processing_time": 0
}

def process_file(file_path, header_levels=None, skip_steps=None):
    """
    处理单个Markdown文件
    
    Args:
        file_path (str): 文件路径
        header_levels (list, optional): 要处理的标题级别
        skip_steps (list, optional): 要跳过的处理步骤
        
    Returns:
        bool: 处理是否成功
    """
    logger = logging.getLogger("MarkoProcessor")
    skip_steps = skip_steps or []
    
    try:
        print(f"{Fore.CYAN}处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_length = len(content)
        logger.info(f"成功读取文件，字符数: {original_length}")
        stats["total_chars_processed"] += original_length
        
        start_time = time.time()
        
        # 1. 保护代码块
        if 'code_protect' not in skip_steps:
            logger.info("保护代码块")
            code_protector = CodeProtectorTransformer()
            content = code_protector.transform(content)
        else:
            code_protector = None
        
        # 2. 处理表格
        if 'table' not in skip_steps:
            logger.info("处理表格")
            table_transformer = TableTransformer()
            content = table_transformer.transform(content)
        
        # 3. 处理标题
        if 'header' not in skip_steps:
            logger.info(f"处理标题，级别: {header_levels}")
            header_transformer = HeaderTransformer(header_levels)
            content = header_transformer.transform(content)
        
        # 4. 处理文本格式化
        if 'text' not in skip_steps:
            logger.info("处理文本格式化")
            text_transformer = TextTransformer()
            content = text_transformer.transform(content)
        
        # 5. 恢复代码块
        if code_protector and 'code_protect' not in skip_steps:
            logger.info("恢复代码块")
            content = code_protector.restore_code_blocks(content)
        
        # 处理完成，计算耗时
        end_time = time.time()
        processing_time = end_time - start_time
        stats["processing_time"] += processing_time
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        stats["processed_files"] += 1
        
        # 显示处理结果
        new_length = len(content)
        char_diff = new_length - original_length
        diff_str = f"{char_diff:+d}" if char_diff != 0 else "0"
        
        print(f"{Fore.GREEN}完成: {os.path.basename(file_path)}")
        print(f"  - 处理耗时: {processing_time:.2f}秒")
        print(f"  - 文件大小: {original_length} → {new_length} ({diff_str}字符){Style.RESET_ALL}")
        
        return True
        
    except Exception as e:
        logger.error(f"处理文件失败: {file_path}", exc_info=True)
        print(f"{Fore.RED}处理失败: {str(e)}{Style.RESET_ALL}")
        return False

def process_directory(directory_path, header_levels=None, skip_steps=None, recursive=False):
    """
    处理目录中的所有Markdown文件
    
    Args:
        directory_path (str): 目录路径
        header_levels (list, optional): 要处理的标题级别
        skip_steps (list, optional): 要跳过的处理步骤
        recursive (bool, optional): 是否递归处理子目录
        
    Returns:
        int: 成功处理的文件数量
    """
    print(f"{Fore.CYAN}扫描目录: {directory_path}{Style.RESET_ALL}")
    md_files = []
    
    if recursive:
        # 递归查找所有Markdown文件
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
    else:
        # 只处理当前目录下的Markdown文件
        for file in os.listdir(directory_path):
            if file.lower().endswith('.md'):
                md_files.append(os.path.join(directory_path, file))
    
    if not md_files:
        print(f"{Fore.YELLOW}警告: 目录中没有找到Markdown文件{Style.RESET_ALL}")
        return 0
    
    print(f"{Fore.GREEN}找到 {len(md_files)} 个Markdown文件待处理{Style.RESET_ALL}")
    
    success_count = 0
    for i, file_path in enumerate(md_files):
        print(f"\n{Fore.CYAN}[{i+1}/{len(md_files)}] 处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        if process_file(file_path, header_levels, skip_steps):
            success_count += 1
    
    return success_count

def main():
    """主函数"""
    # 设置日志
    logger = setup_logging()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='基于marko的Markdown内容转换工具')
    parser.add_argument('--path', help='要处理的文件或目录路径')
    parser.add_argument('--header-levels', help='要处理的标题级别，如1,2,3')
    parser.add_argument('--skip', help='要跳过的处理步骤，如code_protect,table,header,text')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    args = parser.parse_args()
    
    try:
        # 解析标题级别
        header_levels = None
        if args.header_levels:
            try:
                header_levels = []
                for part in args.header_levels.split(','):
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
                    header_levels = [1, 2, 3, 4, 5, 6]
                    logger.warning("无效的标题级别输入，使用默认值[1-6]")
            except ValueError:
                header_levels = [1, 2, 3, 4, 5, 6]
                logger.warning(f"无法解析标题级别输入，使用默认值[1-6]")
        else:
            header_levels = [1, 2, 3, 4, 5, 6]
        
        # 解析要跳过的步骤
        skip_steps = []
        if args.skip:
            skip_steps = [step.strip() for step in args.skip.split(',')]
        
        # 确定处理路径
        path = None
        if args.path:
            path = args.path
            if not os.path.exists(path):
                print(f"{Fore.RED}路径无效: {path}{Style.RESET_ALL}")
                return
        else:
            # 使用当前目录
            path = os.getcwd()
            print(f"{Fore.YELLOW}未指定路径，使用当前目录: {path}{Style.RESET_ALL}")
        
        # 如果没有通过命令行指定标题级别，询问用户
        if not args.header_levels:
            try:
                header_input = Prompt.ask(
                    "请输入要处理的标题级别(多个级别用逗号分隔，如1,2,3，或范围如1-3，默认处理所有标题级别1-6)",
                    default="1-6"
                )
                
                if header_input and header_input != "1-6":
                    try:
                        header_levels = []
                        for part in header_input.split(','):
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
                            header_levels = [1, 2, 3, 4, 5, 6]
                            logger.warning("无效的标题级别输入，使用默认值[1-6]")
                    except ValueError:
                        header_levels = [1, 2, 3, 4, 5, 6]
                        logger.warning(f"无法解析标题级别输入'{header_input}'，使用默认值[1-6]")
            except Exception as e:
                logger.error(f"询问标题级别时出错: {str(e)}")
        
        print(f"{Fore.CYAN}将处理标题级别: {header_levels}{Style.RESET_ALL}")
        
        # 处理文件或目录
        if os.path.isfile(path):
            process_file(path, header_levels, skip_steps)
        elif os.path.isdir(path):
            recursive = args.recursive
            if not recursive and not args.recursive:
                # 询问用户是否递归处理子目录
                try:
                    recursive = Confirm.ask("是否递归处理子目录?", default=False)
                except Exception as e:
                    logger.error(f"询问递归处理时出错: {str(e)}")
            
            success_count = process_directory(path, header_levels, skip_steps, recursive)
            
            # 显示总结
            print(f"\n{Fore.GREEN}===== 处理完成 ====={Style.RESET_ALL}")
            print(f"成功处理文件数: {success_count}/{stats['processed_files']}")
            print(f"处理字符总数: {stats['total_chars_processed']}")
            print(f"总处理时间: {stats['processing_time']:.2f}秒")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}", exc_info=True)
        print(f"{Fore.RED}执行失败: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}===== 基于marko的Markdown内容转换工具 ====={Style.RESET_ALL}")
    main()
