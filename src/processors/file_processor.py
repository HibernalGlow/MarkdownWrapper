"""
文件处理模块，处理单个Markdown文件或目录中的多个文件
"""
import os
import time
from colorama import Fore, Style
from ..utils.logger import logger
from ..utils.statistics import stats
from .text_processor import process_text

def process_file(file_path, header_levels=None):
    """处理单个文件"""
    try:
        print(f"{Fore.CYAN}处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        original_length = len(text)
        logger.info(f"成功读取文件，字符数: {original_length}")
        
        # 处理文本
        start_time = time.time()
        processed_text = process_text(text, header_levels)
        end_time = time.time()
        
        # 更新统计
        stats.increment_processed_files()
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(processed_text)
        
        new_length = len(processed_text)
        char_diff = new_length - original_length
        diff_str = f"{char_diff:+d}" if char_diff != 0 else "0"
        
        print(f"{Fore.GREEN}完成: {os.path.basename(file_path)} ")
        print(f"  - 处理耗时: {end_time - start_time:.2f}秒")
        print(f"  - 文件大小: {original_length} → {new_length} ({diff_str}字符)")
        print(f"  - 应用规则: {sum(stats.get_pattern_matches().values())}次匹配{Style.RESET_ALL}")
        
        return True
    except Exception as e:
        logger.error(f"处理文件失败: {file_path}", exc_info=True)
        print(f"{Fore.RED}处理失败: {str(e)}{Style.RESET_ALL}")
        return False

def process_directory(directory_path, header_levels=None, recursive=False):
    """处理目录中的所有 Markdown 文件"""
    print(f"{Fore.CYAN}扫描目录: {directory_path}{Style.RESET_ALL}")
    md_files = []
    
    # 查找所有 Markdown 文件
    if recursive:
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
    else:
        # 只处理目录下的MD文件，不递归
        md_files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) 
                   if f.lower().endswith('.md') and os.path.isfile(os.path.join(directory_path, f))]
    
    if not md_files:
        print(f"{Fore.YELLOW}警告: 目录中没有找到 Markdown 文件{Style.RESET_ALL}")
        return
    
    print(f"{Fore.GREEN}找到 {len(md_files)} 个 Markdown 文件待处理{Style.RESET_ALL}")
    
    # 处理每个文件
    for i, file_path in enumerate(md_files):
        print(f"\n{Fore.CYAN}[{i+1}/{len(md_files)}] 处理文件: {os.path.basename(file_path)}{Style.RESET_ALL}")
        process_file(file_path, header_levels)
    
    # 显示总结
    print(f"\n{Fore.GREEN}===== 处理完成 ====={Style.RESET_ALL}")
    print(f"处理文件数: {stats.get_all_stats()['processed_files']}")
    print(f"处理字符数: {stats.get_all_stats()['total_chars_processed']}")
    print(f"格式化次数: {stats.get_all_stats()['format_changes']}")
    
    # 显示各种模式的匹配次数
    pattern_matches = stats.get_pattern_matches()
    if pattern_matches:
        print(f"\n{Fore.CYAN}替换规则统计:{Style.RESET_ALL}")
        for pattern, count in sorted(pattern_matches.items(), key=lambda x: x[1], reverse=True):
            if isinstance(pattern, str) and len(pattern) > 50:
                pattern_display = pattern[:47] + "..."
            else:
                pattern_display = pattern
            print(f"  - {pattern_display}: {count}次")