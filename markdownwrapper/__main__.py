"""
Markdown 格式化工具主程序入口
重构版本，使用core模块化设计
"""
import os
import sys
import argparse
import logging
import time
from datetime import datetime
from colorama import init, Fore, Style
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.logging import RichHandler

# 初始化 colorama
init()

# 创建Rich控制台
console = Console()

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)

# 导入项目核心模块
from markdownwrapper.core.markdown_processor import MarkdownProcessor
from markdownwrapper.core.statistics import stats

def setup_logger():
    """配置日志记录器"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建文件处理器
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"markdown_processor_{timestamp}.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levellevelname)s - %(message)s'))
    
    # 添加到日志记录器
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    
    return logger, log_file

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
            logging.warning("无效的标题级别输入，使用默认值[1-6]")
            return list(range(1, 7))
        else:
            return header_levels
    except ValueError:
        logging.warning(f"无法解析输入 '{header_levels_input}'，使用默认值[1-6]")
        return list(range(1, 7))

def display_welcome_message():
    """显示欢迎信息"""
    console.print(Panel.fit(
        "[bold magenta]Markdown 格式化工具[/bold magenta]\n"
        "[cyan]重构版本，使用core模块化设计[/cyan]",
        title="欢迎使用",
        border_style="blue"
    ))

def display_statistics():
    """显示处理统计信息"""
    summary = stats.get_summary()
    
    table = Table(title="处理统计", show_header=True, header_style="bold magenta")
    table.add_column("指标", style="dim")
    table.add_column("值", justify="right")
    
    table.add_row("处理文件数", str(summary["processed_files"]))
    table.add_row("处理字符数", str(summary["total_chars"]))
    table.add_row("格式修改次数", str(summary["format_changes"]))
    table.add_row("模式匹配次数", str(summary["pattern_matches_count"]))
    
    # 计算处理时间
    if summary["processing_time"] > 60:
        time_str = f"{summary['processing_time'] / 60:.2f} 分钟"
    else:
        time_str = f"{summary['processing_time']:.2f} 秒"
    table.add_row("处理时间", time_str)
    
    console.print(table)
    
    # 显示模式匹配统计
    display_pattern_statistics()

def display_pattern_statistics():
    """显示模式匹配统计信息"""
    pattern_stats = stats.get_pattern_stats()
    if pattern_stats:
        console.print("\n[bold cyan]替换规则统计:[/bold cyan]")
        pattern_table = Table(show_header=True)
        pattern_table.add_column("规则", style="dim")
        pattern_table.add_column("匹配次数", justify="right")
        
        # 按匹配次数排序
        sorted_patterns = sorted(pattern_stats.items(), key=lambda x: x[1], reverse=True)
        for pattern, count in sorted_patterns[:10]:  # 只显示前10个
            if isinstance(pattern, str) and len(pattern) > 50:
                pattern_display = pattern[:47] + "..."
            else:
                pattern_display = str(pattern)
            pattern_table.add_row(pattern_display, str(count))
        
        if len(pattern_stats) > 10:
            pattern_table.add_row("...", f"等 {len(pattern_stats) - 10} 个更多模式")
            
        console.print(pattern_table)

def process_file(file_path, header_levels=None, output_dir=None, skip_steps=None):
    """处理单个Markdown文件"""
    try:
        # 创建处理器实例
        processor = MarkdownProcessor(output_dir=output_dir)
        
        # 记录开始时间
        stats.start_timer()
        
        # 进行处理
        output_path = processor.process(file_path, header_levels=header_levels, skip_steps=skip_steps or [])
        
        # 记录结束时间
        stats.stop_timer()
        
        # 更新统计信息
        stats.add_processed_file()
        
        if output_path and output_path != file_path:
            # 获取文件大小
            original_size = os.path.getsize(file_path)
            new_size = os.path.getsize(output_path)
            
            # 更新统计
            stats.add_chars_processed(new_size)
            
            # 显示处理结果
            console.print(f"[green]✓ 文件处理完成:[/green] {os.path.basename(file_path)}")
            console.print(f"  - 输出文件: {output_path}")
            console.print(f"  - 文件大小: {original_size} → {new_size} ({new_size-original_size:+d} 字节)")
            console.print(f"  - 处理耗时: {stats.stats['processing_time']:.2f}秒")
            
            return output_path
        else:
            console.print(f"[yellow]⚠ 处理未改变文件: {os.path.basename(file_path)}[/yellow]")
            return file_path
    except Exception as e:
        logging.error(f"处理文件失败: {file_path}", exc_info=True)
        console.print(f"[red]✗ 处理失败: {str(e)}[/red]")
        return None

def process_directory(directory_path, header_levels=None, recursive=False, output_dir=None, skip_steps=None):
    """处理目录中的所有Markdown文件"""
    console.print(f"[blue]{'递归' if recursive else ''}扫描目录: {directory_path}[/blue]")
    md_files = []
    
    # 查找所有Markdown文件
    if recursive:
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(os.path.join(root, file))
    else:
        md_files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) 
                   if f.lower().endswith('.md') and os.path.isfile(os.path.join(directory_path, f))]
    
    if not md_files:
        console.print(f"[yellow]警告: 目录中没有找到Markdown文件[/yellow]")
        return
    
    console.print(f"[green]找到 {len(md_files)} 个Markdown文件待处理[/green]")
    
    # 处理每个文件
    results = []
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
            
            # 处理文件
            output_path = process_file(file_path, header_levels, output_dir, skip_steps)
            if output_path:
                results.append(output_path)
            
            progress.update(file_task, completed=1)
            progress.update(overall_task, advance=1)
    
    console.print(f"[bold green]✓ 处理完成! 共处理 {len(results)} 个文件[/bold green]")
    return results

def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Markdown 文件格式化工具')
    parser.add_argument('--path', help='要处理的文件或目录路径')
    parser.add_argument('-o', '--output', help='输出目录路径')
    parser.add_argument('-c', '--clipboard', action='store_true', help='从剪贴板读取路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理目录')
    parser.add_argument('--headers', help='要处理的标题级别，如"1,2,3"或"1-3,5"')
    parser.add_argument('--skip', help='要跳过的处理步骤，逗号分隔，可选值: format,table,header,pattern')
    parser.add_argument('--log-file', help='日志文件路径')
    args = parser.parse_args()
    
    try:
        # 设置日志
        logger, log_file = setup_logger()
        logger.info("开始执行Markdown处理工具")
        
        # 显示欢迎信息
        display_welcome_message()
        console.print(f"[dim]日志将保存到: {log_file}[/dim]")
        
        # 获取输出目录
        output_dir = args.output
        if output_dir:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            console.print(f"[blue]输出目录: {output_dir}[/blue]")
        else:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
            os.makedirs(output_dir, exist_ok=True)
            console.print(f"[blue]使用默认输出目录: {output_dir}[/blue]")
        
        # 获取要跳过的处理步骤
        skip_steps = []
        if args.skip:
            skip_steps = [step.strip() for step in args.skip.split(',')]
            valid_steps = ['format', 'table', 'header', 'pattern']
            skip_steps = [step for step in skip_steps if step in valid_steps]
            if skip_steps:
                console.print(f"[yellow]将跳过以下处理步骤: {', '.join(skip_steps)}[/yellow]")
        
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
            default_path = os.path.join(current_dir, 'examples', '1.md')
            if not os.path.exists(default_path):
                default_path = current_dir
                
            path = Prompt.ask(
                "请输入要处理的文件或目录路径",
                default=default_path
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
            # 单个文件处理
            process_file(path, header_levels, output_dir, skip_steps)
        elif os.path.isdir(path):
            # 目录处理
            recursive = args.recursive
            if not args.recursive and not args.path:  # 只在交互模式下询问
                recursive = Confirm.ask("是否递归处理子目录?", default=False)
            
            process_directory(path, header_levels, recursive, output_dir, skip_steps)
        
        # 显示统计信息
        console.print("\n")
        display_statistics()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]处理被用户中断[/yellow]")
    except Exception as e:
        logging.error(f"主程序执行失败: {str(e)}", exc_info=True)
        console.print(f"[bold red]执行失败: {str(e)}[/bold red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == '__main__':
    main()