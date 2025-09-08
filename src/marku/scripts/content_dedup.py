import re
import sys
import os
import argparse
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich import print as rprint

console = Console()

def deduplicate_titles(content, title_levels=None):
    """
    对文本内容中的指定级别标题进行去重处理
    
    参数:
        content (str): 要处理的文本内容
        title_levels (list): 要处理的标题级别列表，例如 [1, 2, 3]，如果为None则处理所有级别(1-6)
    
    返回:
        tuple: (处理后的文本内容, 去重统计信息)
    """
    if title_levels is None:
        title_levels = list(range(1, 7))  # 默认处理所有1-6级标题
    
    # 转换为集合以便快速查找
    title_levels_set = set(title_levels)
    
    # 记录已经出现过的标题
    seen_titles = {}
    # 记录去重统计
    stats = {level: {'total': 0, 'duplicated': 0, 'titles': []} for level in title_levels}
    
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        # 使用正则表达式匹配所有级别的标题
        match = re.match(r'^(#{1,6})\s+(.+)$', line)
        
        if match:
            # 获取标题级别和内容
            hashes, title_text = match.groups()
            level = len(hashes)
            
            # 检查是否是需要处理的标题级别
            if level in title_levels_set:
                # 标准化标题文本（去除首尾空格并转换为小写）
                normalized_title = title_text.strip().lower()
                stats[level]['total'] += 1
                
                # 检查标题是否重复
                if normalized_title in seen_titles.get(level, set()):
                    # 标题重复，跳过
                    stats[level]['duplicated'] += 1
                    stats[level]['titles'].append(title_text.strip())
                    continue
                
                # 记录标题
                if level not in seen_titles:
                    seen_titles[level] = set()
                seen_titles[level].add(normalized_title)
        
        # 添加当前行到结果中
        result_lines.append(line)
    
    return '\n'.join(result_lines), stats

def deduplicate_images(content):
    """
    对文本内容中的图片链接进行去重处理
    
    参数:
        content (str): 要处理的文本内容
    
    返回:
        tuple: (处理后的文本内容, 去重统计信息)
    """
    # 图片链接正则表达式
    img_pattern = r'!\[(.*?)\]\((.*?)\)'
    
    # 记录已经出现过的图片链接
    seen_images = set()
    # 记录去重统计
    stats = {'total': 0, 'duplicated': 0, 'images': []}
    
    lines = content.split('\n')
    result_lines = []
    
    for line in lines:
        # 查找行中的所有图片链接
        images = re.findall(img_pattern, line)
        
        # 如果这行没有图片链接，直接添加
        if not images:
            result_lines.append(line)
            continue
        
        # 处理这行中的图片链接
        current_line = line
        for alt_text, img_url in images:
            # 精确匹配图片URL，不进行标准化以确保完全一致
            stats['total'] += 1
            
            # 检查链接是否重复
            if img_url in seen_images:
                # 图片链接重复，从行中删除这个图片链接
                stats['duplicated'] += 1
                stats['images'].append(f"![{alt_text}]({img_url})")
                current_line = current_line.replace(f"![{alt_text}]({img_url})", "", 1)
            else:
                # 记录图片链接
                seen_images.add(img_url)
        
        # 如果处理后的行不为空（或只包含空格），则添加到结果
        if current_line.strip():
            result_lines.append(current_line)
    
    return '\n'.join(result_lines), stats
def setup_presets_dir():
    """设置预设目录"""
    presets_dir = Path.home() / ".glowtoolbox" / "presets"
    presets_dir.mkdir(parents=True, exist_ok=True)
    presets_file = presets_dir / "content_dedup_presets.json"
    return presets_dir, presets_file

def load_presets(presets_file):
    """加载预设配置"""
    if presets_file.exists():
        try:
            with open(presets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[yellow]加载预设失败: {e}[/yellow]")
    return {}

def save_preset(presets_file, name, config):
    """保存预设配置"""
    presets = load_presets(presets_file)
    presets[name] = config
    try:
        with open(presets_file, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        console.print(f"[green]预设 '{name}' 已保存[/green]")
    except Exception as e:
        console.print(f"[red]保存预设失败: {e}[/red]")

def show_presets(presets_file):
    """显示预设列表并选择"""
    presets = load_presets(presets_file)
    if not presets:
        console.print("[yellow]没有找到保存的预设[/yellow]")
        return None

    console.print("\n[bold]已保存的预设:[/bold]")
    for i, (name, config) in enumerate(presets.items(), 1):
        title_levels = config.get("title_levels", [1, 2, 3, 4, 5, 6])
        title_levels_str = ",".join(map(str, title_levels))
        dedup_titles = "是" if config.get("dedup_titles", True) else "否"
        dedup_images = "是" if config.get("dedup_images", False) else "否"
        
        console.print(f"{i}. [cyan]{name}[/cyan] (标题级别: {title_levels_str}, "
                    f"标题去重: {dedup_titles}, 图片去重: {dedup_images})")
    
    choice = Prompt.ask("\n选择预设编号，或按回车跳过", default="")
    if not choice:
        return None
    
    try:
        index = int(choice) - 1
        if 0 <= index < len(presets):
            preset_name = list(presets.keys())[index]
            return preset_name, presets[preset_name]
        else:
            console.print("[yellow]无效的选择，使用默认配置[/yellow]")
            return None
    except ValueError:
        console.print("[yellow]无效的输入，使用默认配置[/yellow]")
        return None

def main():
    console.print(Panel.fit("Markdown内容去重工具", style="bold blue", subtitle="处理Markdown文件中的重复标题和图片链接"))
    
    # 设置预设目录
    presets_dir, presets_file = setup_presets_dir()
    
    # 显示并选择预设
    preset_result = show_presets(presets_file)
    config = {}
    
    if preset_result:
        preset_name, config = preset_result
        console.print(f"\n[green]已加载预设: [bold]{preset_name}[/bold][/green]")
    
    # 使用argparse解析命令行参数
    parser = argparse.ArgumentParser(description="处理Markdown文件中的重复标题和图片链接")
    parser.add_argument("file", nargs="?", help="要处理的Markdown文件路径")
    parser.add_argument("--title-levels", "-t", help="要处理的标题级别，用逗号分隔，例如：1,2,3")
    parser.add_argument("--no-title", action="store_true", help="不进行标题去重")
    parser.add_argument("--images", "-i", action="store_true", help="进行图片链接去重")
    
    args = parser.parse_args()
    
    # 默认处理同级目录下的1.md
    default_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "1.md")
    
    # 检查文件路径
    if args.file:
        file_path = args.file
    else:
        # 如果没有通过命令行指定文件，使用交互式输入
        file_path = Prompt.ask(
            "请输入要处理的Markdown文件路径",
            default=default_file if os.path.exists(default_file) else ""
        )
        if not file_path:
            if os.path.exists(default_file):
                file_path = default_file
                console.print(f"使用默认文件: [bold green]{default_file}[/]")
            else:
                console.print(f"[bold red]错误:[/] 没有指定文件路径", style="red")
                return
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        console.print(f"[bold red]错误:[/] 文件 '{file_path}' 不存在", style="red")
        return
    
    # 从配置或命令行参数确定去重标题的级别
    dedup_titles = not args.no_title if args else config.get("dedup_titles", True)
    title_levels_input = args.title_levels if args and args.title_levels else None
    
    if title_levels_input:
        try:
            title_levels = [int(level) for level in title_levels_input.split(',')]
            # 确保所有级别都在1-6范围内
            title_levels = [level for level in title_levels if 1 <= level <= 6]
        except ValueError:
            console.print("[bold red]错误:[/] 标题级别必须是1到6之间的整数，用逗号分隔", style="red")
            return
    else:
        # 如果没有命令行参数，使用预设或交互式输入
        title_levels = config.get("title_levels", list(range(1, 7)))
        
        if not preset_result:  # 如果没有使用预设，使用交互式输入
            title_levels_str = Prompt.ask(
                "请输入要处理的标题级别，用逗号分隔",
                default=",".join(map(str, title_levels))
            )
            try:
                title_levels = [int(level) for level in title_levels_str.split(',')]
                # 确保所有级别都在1-6范围内
                title_levels = [level for level in title_levels if 1 <= level <= 6]
            except ValueError:
                console.print("[bold red]错误:[/] 标题级别必须是1到6之间的整数，用逗号分隔", style="red")
                return
    
    # 从配置或命令行参数确定是否去重图片
    dedup_images = args.images if args else config.get("dedup_images", False)
    
    if not preset_result:  # 如果没有使用预设，使用交互式输入
        dedup_titles = Confirm.ask("是否进行标题去重?", default=dedup_titles)
        dedup_images = Confirm.ask("是否进行图片链接去重?", default=dedup_images)
    
    # 如果两个功能都禁用，提示用户并退出
    if not dedup_titles and not dedup_images:
        console.print("[bold yellow]警告:[/] 未启用任何处理功能。请启用标题去重或图片链接去重功能。")
        return
    
    # 使用进度指示器读取文件
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("正在读取文件...", total=1)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            progress.update(task, advance=1)
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]读取文件时出错:[/] {e}", style="red")
            return
    
    # 使用进度指示器处理去重
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # 初始化变量
        title_stats = None
        image_stats = None
        
        # 标题去重处理
        if dedup_titles:
            task = progress.add_task(f"正在处理标题去重 (级别: {','.join(map(str, title_levels))})...", total=1)
            content, title_stats = deduplicate_titles(content, title_levels)
            progress.update(task, advance=1)
        
        # 图片链接去重处理
        if dedup_images:
            task = progress.add_task("正在处理图片链接去重...", total=1)
            content, image_stats = deduplicate_images(content)
            progress.update(task, advance=1)
    
    # 构建输出文件名
    base_name, ext = os.path.splitext(file_path)
    output_file = f"{base_name}{ext}"
    
    # 使用进度指示器写入结果到新文件
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("正在写入结果...", total=1)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                file.write(content)
            progress.update(task, advance=1)
        except Exception as e:
            progress.stop()
            console.print(f"[bold red]写入文件时出错:[/] {e}", style="red")
            return
    
    # 显示标题去重统计信息
    if dedup_titles and title_stats:
        table = Table(title="标题去重统计", show_header=True, header_style="bold magenta")
        table.add_column("标题级别", justify="center")
        table.add_column("总数", justify="center")
        table.add_column("重复数", justify="center")
        table.add_column("重复率", justify="center")
        
        has_title_duplicates = False
        total_title_count = 0
        total_title_duplicated = 0
        
        for level in sorted(title_stats.keys()):
            total = title_stats[level]['total']
            duplicated = title_stats[level]['duplicated']
            total_title_count += total
            total_title_duplicated += duplicated
            
            if duplicated > 0:
                has_title_duplicates = True
                percentage = f"{duplicated / total * 100:.1f}%" if total > 0 else "0%"
                table.add_row(
                    f"H{level}",
                    str(total),
                    f"[red]{duplicated}[/]",
                    f"[red]{percentage}[/]"
                )
            else:
                percentage = "0%" if total > 0 else "N/A"
                table.add_row(f"H{level}", str(total), "0", percentage)
        
        # 添加总计行
        if total_title_count > 0:
            percentage = f"{total_title_duplicated / total_title_count * 100:.1f}%" if total_title_count > 0 else "0%"
            table.add_row(
                "[bold]总计[/]",
                f"[bold]{total_title_count}[/]",
                f"[bold {'red' if total_title_duplicated > 0 else 'white'}]{total_title_duplicated}[/]",
                f"[bold {'red' if total_title_duplicated > 0 else 'white'}]{percentage}[/]"
            )
        
        console.print(table)
        
        # 如果有重复标题，显示详细信息
        if has_title_duplicates:
            console.print("\n[bold yellow]重复标题列表:[/]")
            for level in sorted(title_stats.keys()):
                if title_stats[level]['duplicated'] > 0:
                    console.print(f"\n[bold]H{level} 级标题重复:[/]")
                    for i, title in enumerate(title_stats[level]['titles']):
                        console.print(f"  {i+1}. [italic]{title}[/]")
    
    # 显示图片链接去重统计信息
    if dedup_images and image_stats:
        console.print("\n[bold blue]图片链接去重统计:[/]")
        total_images = image_stats['total']
        duplicated_images = image_stats['duplicated']
        percentage = f"{duplicated_images / total_images * 100:.1f}%" if total_images > 0 else "0%"
        
        image_table = Table(show_header=True, header_style="bold magenta")
        image_table.add_column("项目", justify="center")
        image_table.add_column("数量", justify="center")
        
        image_table.add_row("总图片链接数", f"{total_images}")
        image_table.add_row("重复图片链接数", f"[{'red' if duplicated_images > 0 else 'white'}]{duplicated_images}[/]")
        image_table.add_row("重复率", f"[{'red' if duplicated_images > 0 else 'white'}]{percentage}[/]")
        
        console.print(image_table)
        
        # 如果有重复图片链接，显示详细信息
        if duplicated_images > 0:
            console.print("\n[bold yellow]重复图片链接列表:[/]")
            for i, image in enumerate(image_stats['images']):
                console.print(f"  {i+1}. [italic]{image}[/]")
    
    console.print(f"\n[bold green]处理完成！[/] 输出文件: [bold blue]{output_file}[/]")
    console.print(f"原始文件大小: [cyan]{os.path.getsize(file_path):,}[/] 字节")
    console.print(f"处理后文件大小: [cyan]{os.path.getsize(output_file):,}[/] 字节")
    
    # 询问是否保存为预设
    if Confirm.ask("是否保存当前配置为预设?", default=False):
        preset_name = Prompt.ask("请输入预设名称")
        if preset_name:
            # 保存当前配置
            current_config = {
                "title_levels": title_levels,
                "dedup_titles": dedup_titles,
                "dedup_images": dedup_images
            }
            save_preset(presets_file, preset_name, current_config)

if __name__ == "__main__":
    main()