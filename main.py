"""
Markdown 格式化工具主程序入口
使用Rich库实现交互式操作界面
"""
import os
import sys
import argparse
from colorama import init, Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

# 初始化 colorama
init()

# 导入项目模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.utils.logger import logger
from src.utils.statistics import stats
from src.processors.file_processor import process_file, process_directory

# 创建Rich控制台
console = Console()

def parse_header_levels(header_levels_input):
    """解析用户输入的标题级别"""
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

def display_welcome_message():
    """显示欢迎信息"""
    console.print(Panel.fit(
        "[bold magenta]Markdown 格式化工具[/bold magenta]",
        title="欢迎使用",
        border_style="blue"
    ))

def display_statistics():
    """显示处理统计信息"""
    all_stats = stats.get_all_stats()
    
    table = Table(title="处理统计", show_header=True, header_style="bold magenta")
    table.add_column("指标", style="dim")
    table.add_column("值", justify="right")
    
    table.add_row("处理文件数", str(all_stats["processed_files"]))
    table.add_row("处理字符数", str(all_stats["total_chars_processed"]))
    table.add_row("格式修改次数", str(all_stats["format_changes"]))
    
    console.print(table)
    
    # 显示模式匹配统计
    # display_pattern_statistics()

def display_pattern_statistics():
    pattern_matches = stats.get_pattern_matches()
    if pattern_matches:
        console.print("\n[bold cyan]替换规则统计:[/bold cyan]")
        pattern_table = Table(show_header=True)
        pattern_table.add_column("规则", style="dim")
        pattern_table.add_column("匹配次数", justify="right")
        
        for pattern, count in sorted(pattern_matches.items(), key=lambda x: x[1], reverse=True)[:10]:  # 只显示前10个
            if isinstance(pattern, str) and len(pattern) > 50:
                pattern_display = pattern[:47] + "..."
            else:
                pattern_display = str(pattern)
            pattern_table.add_row(pattern_display, str(count))
        
        if len(pattern_matches) > 10:
            pattern_table.add_row("...", "...")
            
        console.print(pattern_table)

def process_with_progress(file_path, header_levels):
    """带进度显示的文件处理"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(f"处理 {os.path.basename(file_path)}", total=1000)
            
            # 为了模拟进度，分段更新
            progress.update(task, advance=100)
            
            # 实际处理文本
            from src.processors.text_processor import process_text
            processed_text = process_text(text, header_levels)
            
            progress.update(task, advance=800)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(processed_text)
                
            progress.update(task, advance=100)
        
        console.print(f"[green]✓ 成功处理文件: {os.path.basename(file_path)}[/green]")
        return True
    except Exception as e:
        console.print(f"[red]✗ 处理失败: {str(e)}[/red]")
        logger.error(f"处理文件失败: {file_path}", exc_info=True)
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Markdown 文件格式化工具')
    parser.add_argument('--path', help='要处理的文件或目录路径')
    parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理目录')
    parser.add_argument('--headers', help='要处理的标题级别，如"1,2,3"或"1-3,5"')
    args = parser.parse_args()
    
    try:
        display_welcome_message()
        
        # 获取处理路径
        path = None
        if args.clipboard:
            try:
                import pyperclip
                path = pyperclip.paste().strip().strip('"')
                if not os.path.exists(path):
                    console.print(f"[red]剪贴板中的路径无效: {path}[/red]")
                    return
                console.print(f"[green]从剪贴板读取路径: {path}[/green]")
            except ImportError:
                console.print("[red]未安装pyperclip模块，无法从剪贴板读取[/red]")
                return
        elif args.path:
            path = args.path
            if not os.path.exists(path):
                console.print(f"[red]路径无效: {path}[/red]")
                return
        else:
            # 使用交互方式获取路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            default_path = os.path.join(current_dir, '1.md')
            
            path = Prompt.ask(
                "请输入要处理的文件或目录路径",
                default=default_path if os.path.exists(default_path) else current_dir
            )
            
            if not os.path.exists(path):
                console.print(f"[red]路径无效: {path}[/red]")
                return
        
        # 询问要处理哪几级标题
        header_levels_input = args.headers
        if not header_levels_input:
            header_levels_input = Prompt.ask(
                "请输入要处理的标题级别(多个级别用逗号分隔，如1,2,3，范围如1-3，默认处理所有级别1-6)", 
                default="all"
            )
        
        # 解析标题级别
        header_levels = parse_header_levels(header_levels_input)
        console.print(f"[blue]将处理标题级别: {', '.join(map(str, header_levels))}[/blue]")
        
        # 处理文件或目录
        if os.path.isfile(path):
            process_with_progress(path, header_levels)
        elif os.path.isdir(path):
            # 询问是否递归处理
            recursive = args.recursive
            if not args.recursive and not args.path:  # 只在交互模式下询问
                recursive = Confirm.ask("是否递归处理子目录?", default=False)
            
            # 扫描Markdown文件
            md_files = []
            if recursive:
                console.print(f"[blue]递归扫描目录: {path}[/blue]")
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.md'):
                            md_files.append(os.path.join(root, file))
            else:
                console.print(f"[blue]扫描目录: {path}[/blue]")
                md_files = [os.path.join(path, f) for f in os.listdir(path) 
                           if f.lower().endswith('.md') and os.path.isfile(os.path.join(path, f))]
            
            if not md_files:
                console.print("[yellow]警告: 目录中没有找到 Markdown 文件[/yellow]")
                return
            
            console.print(f"[green]找到 {len(md_files)} 个 Markdown 文件待处理[/green]")
            
            # 询问是否确认处理
            if not Confirm.ask(f"确认处理这 {len(md_files)} 个文件?", default=True):
                console.print("[yellow]已取消操作[/yellow]")
                return
            
            # 处理每个文件
            with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                overall_task = progress.add_task(f"总进度", total=len(md_files))
                
                for i, file_path in enumerate(md_files):
                    progress.update(overall_task, description=f"总进度 ({i+1}/{len(md_files)})")
                    file_task = progress.add_task(f"处理 {os.path.basename(file_path)}", total=1)
                    
                    # 为避免进度条冲突，这里不使用单文件进度
                    from src.processors.file_processor import process_file
                    process_file(file_path, header_levels)
                    
                    progress.update(file_task, completed=1)
                    progress.update(overall_task, advance=1)
            
            console.print("[bold green]✓ 所有文件处理完成![/bold green]")
        
        # 显示统计信息
        display_statistics()
        
    except Exception as e:
        logger.error(f"主程序执行失败: {str(e)}", exc_info=True)
        console.print(f"[bold red]执行失败: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == '__main__':
    main()