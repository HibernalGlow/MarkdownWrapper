"""
标题转换独立脚本：将纯文本转换为标题
"""
import argparse
import os
import sys
import logging
import colorama
from colorama import Fore, Style
from rich.prompt import Prompt

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入HeaderTransformer
from markdownwrapper.core.header_transformer import HeaderTransformer

# 初始化colorama
colorama.init()

def setup_logging():
    """设置日志配置"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    
    return logger

def process_file(file_path, header_levels):
    """
    处理单个Markdown文件，将纯文本转换为标题
    
    Args:
        file_path (str): 文件路径
        header_levels (list): 要处理的标题级别
        
    Returns:
        bool: 处理是否成功
    """
    logger = logging.getLogger("HeaderConverter")
    
    try:
        print(f"{Fore.CYAN}处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        # 创建转换器
        header_transformer = HeaderTransformer(header_levels)
        
        # 处理文件
        output_path = header_transformer.transform_file(file_path)
        
        if output_path:
            print(f"{Fore.GREEN}成功处理文件: {os.path.basename(output_path)}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}处理文件失败: {os.path.basename(file_path)}{Style.RESET_ALL}")
            return False
            
    except Exception as e:
        logger.error(f"处理文件失败: {file_path}", exc_info=True)
        print(f"{Fore.RED}处理失败: {str(e)}{Style.RESET_ALL}")
        return False

def main():
    """主函数"""
    # 设置日志
    logger = setup_logging()
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Markdown标题转换工具：将纯文本转换为标题')
    parser.add_argument('--path', help='要处理的文件或目录路径')
    parser.add_argument('--header-levels', help='要处理的标题级别，如1,2,3')
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
            # 询问用户要处理哪几级标题
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
                else:
                    header_levels = [1, 2, 3, 4, 5, 6]
            except Exception as e:
                header_levels = [1, 2, 3, 4, 5, 6]
                logger.error(f"询问标题级别时出错: {str(e)}，使用默认值[1-6]")
        
        print(f"{Fore.CYAN}将处理标题级别: {header_levels}{Style.RESET_ALL}")
        
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
        
        # 处理文件或目录
        if os.path.isfile(path):
            process_file(path, header_levels)
        elif os.path.isdir(path):
            # 处理目录下的所有Markdown文件
            md_files = [os.path.join(path, f) for f in os.listdir(path) 
                       if f.lower().endswith('.md') and os.path.isfile(os.path.join(path, f))]
            
            if not md_files:
                print(f"{Fore.YELLOW}警告: 目录中没有找到Markdown文件{Style.RESET_ALL}")
                return
            
            print(f"{Fore.GREEN}找到 {len(md_files)} 个Markdown文件待处理{Style.RESET_ALL}")
            
            success_count = 0
            for i, file_path in enumerate(md_files):
                print(f"\n{Fore.CYAN}[{i+1}/{len(md_files)}] 处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
                if process_file(file_path, header_levels):
                    success_count += 1
            
            print(f"\n{Fore.GREEN}===== 处理完成 ====={Style.RESET_ALL}")
            print(f"成功处理文件数: {success_count}/{len(md_files)}")
        
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}", exc_info=True)
        print(f"{Fore.RED}执行失败: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    print(f"{Fore.CYAN}===== Markdown标题转换工具 ====={Style.RESET_ALL}")
    main()
