import re
import os
import argparse
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

console = Console()

def process_ordered_lists(content: str) -> str:
    """处理Markdown文件中的单行有序列表，如果一个有序列表上下3行没有有序列表，则将". "替换为"."
    
    Args:
        content: Markdown内容字符串
        
    Returns:
        处理后的内容
    """
    lines = content.split('\n')
    modified_lines = lines.copy()
    pattern = re.compile(r'^\s*\d+\.\s')  # 匹配有序列表模式：数字+点+空格
    
    # 标记每一行是否为有序列表项
    is_ordered_list = [bool(pattern.match(line)) for line in lines]
    
    # 处理每一行
    for i in range(len(lines)):
        if is_ordered_list[i]:
            # 检查上下3行是否有其他有序列表项
            is_isolated = True
            
            # 检查上面3行
            for j in range(max(0, i-3), i):
                if is_ordered_list[j]:
                    is_isolated = False
                    break
            
            # 如果上面没有相关项，检查下面3行
            if is_isolated:
                for j in range(i+1, min(i+4, len(lines))):
                    if is_ordered_list[j]:
                        is_isolated = False
                        break
            
            # 如果这是一个独立的有序列表项，替换". "为"."
            if is_isolated:
                # 使用正则表达式替换第一个". "为"."
                modified_lines[i] = re.sub(r'(\d+)\.\s', r'\1.', lines[i], count=1)
                console.print(f"[yellow]替换行 {i+1}:[/] {lines[i]} -> {modified_lines[i]}")
    
    return '\n'.join(modified_lines)

def process_file(filename: str) -> Tuple[int, List[str]]:
    """处理单个Markdown文件
    
    Args:
        filename: 要处理的文件名
        
    Returns:
        元组，包含处理的条目数和错误消息列表
    """
    console.print(f"[bold blue]处理文件:[/] {filename}")
    
    if not os.path.exists(filename):
        console.print(f"[bold red]错误:[/] 文件 {filename} 不存在")
        return 0, [f"文件 {filename} 不存在"]
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        console.print(f"[bold red]读取文件出错:[/] {str(e)}")
        return 0, [f"读取文件出错: {str(e)}"]
    
    # 保存原始内容以便比较
    original_content = content
    
    # 处理有序列表
    modified_content = process_ordered_lists(content)
    
    # 计算修改的行数
    changes_count = sum(1 for a, b in zip(original_content.split('\n'), modified_content.split('\n')) if a != b)
    
    if changes_count == 0:
        console.print("[yellow]未找到需要处理的单行有序列表[/]")
        return 0, []
    
    try:
        # 写入更新后的内容到文件
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(modified_content)
        console.print(Panel(f"[bold green]成功处理 {changes_count} 行有序列表[/]", 
                          title="处理完成", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]写入文件出错:[/] {str(e)}")
        return changes_count, [f"写入文件出错: {str(e)}"]
    
    return changes_count, []

def process_directory(directory: str, recursive: bool = False) -> Tuple[int, int]:
    """处理目录中的所有.md文件
    
    Args:
        directory: 要处理的目录
        recursive: 是否递归处理子目录
        
    Returns:
        元组，包含处理的文件数和修改的行数
    """
    console.print(f"[bold blue]处理目录:[/] {directory}")
    
    if not os.path.isdir(directory):
        console.print(f"[bold red]错误:[/] 目录 {directory} 不存在")
        return 0, 0
    
    total_files = 0
    total_changes = 0
    
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        
        if os.path.isfile(full_path) and full_path.lower().endswith('.md'):
            changes, _ = process_file(full_path)
            total_changes += changes
            if changes > 0:
                total_files += 1
        elif os.path.isdir(full_path) and recursive:
            files, changes = process_directory(full_path, recursive)
            total_files += files
            total_changes += changes
    
    return total_files, total_changes

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='处理Markdown文件中的单行有序列表，将独立的有序列表中的". "替换为"."')
    parser.add_argument('path', nargs='?', default=None, help='要处理的文件或目录路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('-d', '--demo', action='store_true', help='运行演示，处理当前目录下的1.md文件')
    
    args = parser.parse_args()
    
    path = args.path
    if not path and not args.demo:
        # 默认处理当前目录下的1.md文件
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.md')
        process_file(filename)
        return
    
    if args.demo:
        # 演示模式，处理1.md文件
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.md')
        process_file(filename)
        return
        
    if os.path.isdir(path):
        files, changes = process_directory(path, args.recursive)
        console.print(Panel(f"[bold green]共处理了 {files} 个文件，修改了 {changes} 处有序列表[/]", 
                          title="处理完成", border_style="green"))
    elif os.path.isfile(path):
        process_file(path)
    else:
        console.print(f"[bold red]错误:[/] 路径 {path} 不存在")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]用户中断，程序已停止[/]")
    except Exception as e:
        console.print(f"[bold red]程序发生错误:[/] {str(e)}")