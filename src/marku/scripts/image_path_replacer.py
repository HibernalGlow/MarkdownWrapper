import re
import os
import argparse
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print as rprint
import sys
console = Console()

def replace_image_paths(content: str, relative_path_pattern: str, base_url: str) -> str:
    """替换 Markdown 中的图片相对路径为绝对 URL 地址
    
    Args:
        content: Markdown 内容字符串
        relative_path_pattern: 相对路径模式，例如 "images/"
        base_url: 基础 URL 地址，用于前缀
        
    Returns:
        处理后的内容
    """
    # 转义相对路径模式中的特殊字符，以便在正则表达式中使用
    escaped_pattern = re.escape(relative_path_pattern)
    
    # 构造匹配模式：![任意文本](相对路径模式任意路径)
    pattern = re.compile(fr'!\[(.*?)\]\(({escaped_pattern}[^)]+)\)')
    
    def replace_match(match):
        alt_text = match.group(1)
        relative_path = match.group(2)
        
        # 组合新的绝对路径
        # 从相对路径中提取后面的部分
        path_suffix = relative_path[len(relative_path_pattern):]
        absolute_path = f"{base_url}{path_suffix}"
        
        return f"![{alt_text}]({absolute_path})"
    
    # 替换所有匹配项
    modified_content = pattern.sub(replace_match, content)
    
    return modified_content

def process_file(filename: str, relative_path_pattern: str, base_url: str) -> Tuple[int, List[str]]:
    """处理单个 Markdown 文件中的图片路径
    
    Args:
        filename: 要处理的文件名
        relative_path_pattern: 相对路径模式，例如 "images/"
        base_url: 基础 URL 地址，用于前缀
        
    Returns:
        元组，包含替换的数量和错误消息列表
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
    
    # 替换图片路径
    modified_content = replace_image_paths(content, relative_path_pattern, base_url)
    
    # 计算替换的数量
    escaped_pattern = re.escape(relative_path_pattern)
    count = len(re.findall(fr'!\[(.*?)\]\(({escaped_pattern}[^)]+)\)', original_content))
    
    if count == 0:
        console.print("[yellow]未找到需要替换的图片路径[/]")
        return 0, []
    
    try:
        # 写入更新后的内容到文件
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(modified_content)
        console.print(Panel(f"[bold green]成功替换 {count} 处图片路径[/]", 
                          title="处理完成", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]写入文件出错:[/] {str(e)}")
        return count, [f"写入文件出错: {str(e)}"]
    
    return count, []

def process_directory(directory: str, relative_path_pattern: str, base_url: str, recursive: bool = False) -> Tuple[int, int]:
    """处理目录中的所有.md文件
    
    Args:
        directory: 要处理的目录
        relative_path_pattern: 相对路径模式，例如 "images/"
        base_url: 基础 URL 地址
        recursive: 是否递归处理子目录
        
    Returns:
        元组，包含处理的文件数和替换的路径数
    """
    console.print(f"[bold blue]处理目录:[/] {directory}")
    
    if not os.path.isdir(directory):
        console.print(f"[bold red]错误:[/] 目录 {directory} 不存在")
        return 0, 0
    
    total_files = 0
    total_replacements = 0
    
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        
        if os.path.isfile(full_path) and full_path.lower().endswith('.md'):
            count, _ = process_file(full_path, relative_path_pattern, base_url)
            total_replacements += count
            if count > 0:
                total_files += 1
        elif os.path.isdir(full_path) and recursive:
            files, replacements = process_directory(full_path, relative_path_pattern, base_url, recursive)
            total_files += files
            total_replacements += replacements
    
    return total_files, total_replacements

def interactive_mode() -> Tuple[str, str]:
    """交互式获取用户输入的相对路径模式和基础 URL
    
    Returns:
        元组，包含相对路径模式和基础 URL
    """
    console.print(Panel(
        "[bold]图片路径替换工具[/]\n"
        "此工具会将 Markdown 文档中的相对图片路径替换为绝对 URL 地址",
        title="欢迎使用", border_style="blue"
    ))
    
    # 获取相对路径模式
    relative_path_pattern = Prompt.ask(
        "[bold blue]请输入要替换的相对路径模式[/]", 
        default="images/"
    )
    
    # 获取基础 URL
    base_url = Prompt.ask(
        "[bold blue]请输入要替换为的基础 URL 地址[/]",
        default=""
    )
    
    while not base_url:
        console.print("[bold yellow]基础 URL 不能为空，请重新输入[/]")
        base_url = Prompt.ask(
            "[bold blue]请输入要替换为的基础 URL 地址[/]",
            default=""
        )
    
    # 显示确认信息
    console.print("\n[bold]即将进行以下替换：[/]")
    console.print(f"  [green]将 [bold]![图片描述]({relative_path_pattern}图片路径)[/] 替换为 [bold]![图片描述]({base_url}图片路径)[/][/]")
    
    confirm = Confirm.ask("\n确认进行替换？", default=True)
    if not confirm:
        console.print("[yellow]已取消操作[/]")
        return None, None
    
    return relative_path_pattern, base_url

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='将 Markdown 文件中的相对图片路径替换为绝对 URL 地址')
    parser.add_argument('path', nargs='?', default=None, help='要处理的文件或目录路径')
    parser.add_argument('-p', '--pattern', required=False, default=None, 
                        help='相对路径模式，例如 "images/"')
    parser.add_argument('-b', '--base-url', required=False, default=None,
                        help='基础 URL 地址，用于替换相对路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('-i', '--interactive', action='store_true', help='交互式输入模式')
    parser.add_argument('-d', '--demo', action='store_true', help='运行演示，处理当前目录下的1.md文件')
    
    args = parser.parse_args()
    
    path = args.path
    relative_path_pattern = args.pattern
    base_url = args.base_url
    
    # 如果指定了交互式模式或者缺少必要参数，进入交互式输入
    if args.interactive or len(sys.argv) == 1:
        relative_path_pattern, base_url = interactive_mode()
        if relative_path_pattern is None:
            return
    
    # 如果没有指定相对路径模式，使用默认值
    if not relative_path_pattern:
        relative_path_pattern = "images/"
    
    # 如果没有指定基础 URL 且不是交互式模式，提示错误
    if not base_url and not args.interactive:
        console.print("[bold red]错误:[/] 必须提供基础 URL 地址，使用 -b 参数或 -i 交互式模式")
        return
    
    # 处理文件路径
    if not path and not args.demo:
        # 默认处理当前目录下的1.md文件
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.md')
        process_file(filename, relative_path_pattern, base_url)
        return
    
    if args.demo:
        # 演示模式，处理1.md文件
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.md')
        process_file(filename, relative_path_pattern, base_url)
        return
        
    if os.path.isdir(path):
        files, replacements = process_directory(path, relative_path_pattern, base_url, args.recursive)
        console.print(Panel(f"[bold green]共处理了 {files} 个文件，替换了 {replacements} 处图片路径[/]", 
                          title="处理完成", border_style="green"))
    elif os.path.isfile(path):
        process_file(path, relative_path_pattern, base_url)
    else:
        console.print(f"[bold red]错误:[/] 路径 {path} 不存在")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]用户中断，程序已停止[/]")
    except Exception as e:
        console.print(f"[bold red]程序发生错误:[/] {str(e)}")