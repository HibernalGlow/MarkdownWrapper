import re
import os
import argparse
import urllib.parse
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

def is_image_valid(image_path: str, base_dir: str, check_file_uri: bool = True, check_relative: bool = False) -> bool:
    """检查图片路径是否存在
    
    Args:
        image_path: 图片路径
        base_dir: Markdown文件所在的目录
        check_file_uri: 是否检查 file:/// 类型的链接
        check_relative: 是否检查相对路径类型的链接
        
    Returns:
        如果图片存在或不需要检查则返回 True，否则返回 False
    """
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return True
    
    if image_path.startswith("data:"):
        return True
    
    # 解析文件 URI
    if image_path.startswith("file:///"):
        if not check_file_uri:
            return True
        path_str = image_path[8:]
        path_str = urllib.parse.unquote(path_str)
        if os.name == 'nt' and '/' in path_str:
            path_str = path_str.replace('/', '\\')
        return os.path.exists(path_str)
    
    # 解析其他相对路径或绝对路径
    if check_relative:
        path_str = urllib.parse.unquote(image_path)
        # 处理可能的绝对路径
        if os.path.isabs(path_str):
            return os.path.exists(path_str)
        # 相对路径
        full_path = os.path.join(base_dir, path_str)
        return os.path.exists(full_path)
        
    return True

def remove_missing_images(content: str, base_dir: str, check_file_uri: bool = True, check_relative: bool = False) -> Tuple[str, int]:
    """移除不存在的图片链接
    
    Args:
        content: Markdown 内容字符串
        base_dir: 文件所在的基础目录
        check_file_uri: 是否检查 file:/// 类型的链接
        check_relative: 是否检查相对路径类型的链接
        
    Returns:
        处理后的内容和被移除的图片数
    """
    pattern = re.compile(r'!\[(.*?)\]\(([^)]+)\)')
    removed_count = 0
    
    def replacer(match):
        nonlocal removed_count
        alt_text = match.group(1)
        image_path = match.group(2)
        
        if not is_image_valid(image_path, base_dir, check_file_uri, check_relative):
            console.print(f"[yellow]  移除失效图片: {image_path}[/]")
            removed_count += 1
            return ""  # 移除此图片
        
        return match.group(0)
    
    new_content = pattern.sub(replacer, content)
    return new_content, removed_count

def process_file(filename: str, check_file_uri: bool = True, check_relative: bool = False) -> Tuple[int, List[str]]:
    """处理单个文件
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
    
    base_dir = os.path.dirname(os.path.abspath(filename))
    modified_content, removed_count = remove_missing_images(content, base_dir, check_file_uri, check_relative)
    
    if removed_count == 0:
        return 0, []
    
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(modified_content)
        console.print(Panel(f"[bold green]成功移除 {removed_count} 处失效图片链接[/]", 
                          title="处理完成", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]写入文件出错:[/] {str(e)}")
        return removed_count, [f"写入文件出错: {str(e)}"]
    
    return removed_count, []

def process_directory(directory: str, check_file_uri: bool = True, check_relative: bool = False, recursive: bool = False) -> Tuple[int, int]:
    """处理目录"""
    console.print(f"[bold blue]处理目录:[/] {directory}")
    
    if not os.path.isdir(directory):
        console.print(f"[bold red]错误:[/] 目录 {directory} 不存在")
        return 0, 0
    
    total_files = 0
    total_removed = 0
    
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        
        if os.path.isfile(full_path) and full_path.lower().endswith('.md'):
            removed, _ = process_file(full_path, check_file_uri, check_relative)
            total_removed += removed
            if removed > 0:
                total_files += 1
        elif os.path.isdir(full_path) and recursive:
            files, removed = process_directory(full_path, check_file_uri, check_relative, recursive)
            total_files += files
            total_removed += removed
            
    return total_files, total_removed

def main():
    parser = argparse.ArgumentParser(description='移除 Markdown 文件中失效的图片引用')
    parser.add_argument('path', nargs='?', default=None, help='要处理的文件或目录路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('--check-relative', action='store_true', help='开启相对路径或纯本地路径检查（默认关闭）')
    parser.add_argument('--no-check-file-uri', action='store_true', help='关闭 file:/// 检查（默认开启）')
    
    args = parser.parse_args()
    
    path = args.path
    if not path:
        path = Prompt.ask("请输入要处理的文件或目录路径", default="")
        if not path:
            return
            
    check_file_uri = not args.no_check_file_uri
    check_relative = args.check_relative
    
    if os.path.isdir(path):
        files, removed = process_directory(path, check_file_uri, check_relative, args.recursive)
        console.print(Panel(f"[bold green]共处理了 {files} 个文件，移除了 {removed} 处失效图片[/]", 
                          title="处理完成", border_style="green"))
    elif os.path.isfile(path):
        process_file(path, check_file_uri, check_relative)
    else:
        console.print(f"[bold red]错误:[/] 路径 {path} 不存在")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]用户中断，程序已停止[/]")
    except Exception as e:
        console.print(f"[bold red]程序发生错误:[/] {str(e)}")
