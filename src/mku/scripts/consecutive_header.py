import re
import os
import logging
import argparse # 将被移除
from pathlib import Path
from typing import List, Tuple, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.logging import RichHandler
from rich.prompt import Prompt, Confirm, IntPrompt

# 配置日志
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
#     handlers=[
#         logging.StreamHandler(),
#         # 可以取消注释以启用文件日志记录
#         # logging.FileHandler('consecutive_header_processor.log', encoding='utf-8')
#     ]
# )
# 使用 RichHandler 替换基本配置，以便与 rich.console 更好地集成
# logging 的基本配置现在在 main 函数中根据 verbose 参数设置
console = Console()

class ConsecutiveHeaderProcessor:
    """
    处理 Markdown 文件中连续的同级标题。
    根据所选模式，将连续出现的同级标题转换为普通文本行。
    """
    def __init__(self,
                 input_path: str,
                 output_path: Optional[str] = None,
                 min_consecutive_headers: int = 2,
                 max_blank_lines_between_headers: int = 1,
                 levels_to_process: Optional[List[int]] = None,
                 processing_mode: int = 1):
        """
        初始化处理器。

        Args:
            input_path: 输入 Markdown 文件的路径。
            output_path: 输出文件的路径。如果为 None，则覆盖输入文件。
            min_consecutive_headers: 触发处理的最小连续同级标题数。
                                     例如，设置为 2 表示当出现 2 个或更多连续同级标题时，
                                     根据 processing_mode 开始处理。
            max_blank_lines_between_headers: 允许连续标题之间存在的最大空行数。
                                             超过此数量的空行将中断连续性。
            levels_to_process: 指定要处理的标题级别列表 (1-6)。如果为 None，则处理所有级别。
            processing_mode: 处理模式。
                             1: 从第二个连续同级标题开始转换为普通文本。
                             2: 从第一个连续同级标题开始转换为普通文本。
        """
        self.input_path = Path(input_path)
        self.output_path = Path(output_path) if output_path else self.input_path
        self.min_consecutive_headers = max(2, min_consecutive_headers) # 至少为2才有意义
        self.max_blank_lines_between_headers = max(0, max_blank_lines_between_headers)
        self.levels_to_process = set(levels_to_process) if levels_to_process else set(range(1, 7))
        self.processing_mode = processing_mode

        if not self.input_path.is_file():
            # 这个检查在 main 函数中处理单个文件时更合适，因为 input_path 可能是一个目录
            # logging.warning(f"输入路径 {self.input_path} 不是文件，将在 process_file 中检查。")
            pass


        logging.info(f"初始化 ConsecutiveHeaderProcessor for {self.input_path}:")
        logging.info(f"  输出文件: {self.output_path}")
        logging.info(f"  最小连续标题数: {self.min_consecutive_headers}")
        logging.info(f"  最大允许空行数: {self.max_blank_lines_between_headers}")
        logging.info(f"  处理的标题级别: {sorted(list(self.levels_to_process))}")
        logging.info(f"  处理模式: {self.processing_mode}")

    def _get_header_info(self, line: str) -> Optional[Tuple[int, str]]:
        """
        检查行是否为指定级别的标题，如果是，则返回级别和内容。

        Args:
            line: 要检查的文本行。

        Returns:
            如果行是指定级别的标题，则返回 (level, content) 元组，否则返回 None。
        """
        stripped_line = line.strip()
        if not stripped_line.startswith('#'):
            return None

        level = 0
        for i, char in enumerate(stripped_line):
            if char == '#':
                level += 1
            else:
                # 检查 '#' 后面是否有空格
                if i < len(stripped_line) and stripped_line[i] == ' ':
                    if level in self.levels_to_process:
                        content = stripped_line[i+1:].strip()
                        return level, content
                break # '# ' 结构不满足或遇到非 '#' 字符
        return None # 只有 '#' 或 '#' 后没有空格

    def process_file(self) -> bool:
        """
        处理 Markdown 文件，转换连续的同级标题。

        Returns:
            如果处理成功则返回 True，否则返回 False。
        """
        if not self.input_path.is_file():
            logging.error(f"输入路径不是有效文件: {self.input_path}")
            return False
        try:
            with open(self.input_path, 'r', encoding='utf-8') as infile:
                lines = infile.readlines()

            processed_lines = self._process_lines(lines)

            # 确保输出目录存在
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.output_path, 'w', encoding='utf-8') as outfile:
                outfile.writelines(processed_lines)

            logging.info(f"文件 {self.input_path} 处理成功 -> {self.output_path}")
            return True

        except Exception as e:
            logging.exception(f"处理文件 {self.input_path} 时发生错误")
            return False

    def _process_lines(self, lines: List[str]) -> List[str]:
        """
        核心处理逻辑，遍历行并处理连续标题。

        Args:
            lines: 输入文件的行列表。

        Returns:
            处理后的行列表。
        """
        processed_lines = list(lines) # 创建副本以进行修改
        consecutive_headers_info: List[Tuple[int, int, str]] = [] # (line_index, level, original_line)
        last_header_level: Optional[int] = None
        blank_lines_count = 0

        for i, line in enumerate(lines):
            header_info = self._get_header_info(line)

            if header_info:
                current_level, _ = header_info
                is_consecutive = (
                    last_header_level is not None and
                    current_level == last_header_level and
                    blank_lines_count <= self.max_blank_lines_between_headers
                )

                if is_consecutive:
                    # 是连续的同级标题，添加到列表中
                    consecutive_headers_info.append((i, current_level, line))
                    logging.debug(f"行 {i+1}: 发现连续 {current_level} 级标题。当前连续数量: {len(consecutive_headers_info)}")
                else:
                    # 不是连续的，或者第一个标题
                    # 先处理之前收集的连续标题
                    self._handle_collected_headers(processed_lines, consecutive_headers_info)
                    # 开始新的连续标题序列
                    consecutive_headers_info = [(i, current_level, line)]
                    logging.debug(f"行 {i+1}: 开始新的 {current_level} 级标题序列。")

                last_header_level = current_level
                blank_lines_count = 0 # 重置空行计数器

            elif line.strip() == "":
                # 空行
                blank_lines_count += 1
                # 如果空行过多，中断连续性
                if blank_lines_count > self.max_blank_lines_between_headers:
                     # 如果空行过多，则认为连续性中断，处理已收集的标题
                    if consecutive_headers_info:
                         logging.debug(f"行 {i+1}: 空行过多 ({blank_lines_count} > {self.max_blank_lines_between_headers})，中断连续性。")
                         self._handle_collected_headers(processed_lines, consecutive_headers_info)
                         consecutive_headers_info = []
                         last_header_level = None # 重置级别跟踪

            else:
                # 非标题、非空行
                # 处理之前收集的连续标题
                self._handle_collected_headers(processed_lines, consecutive_headers_info)
                consecutive_headers_info = []
                last_header_level = None # 重置级别跟踪
                blank_lines_count = 0

        # 处理文件末尾可能存在的连续标题
        self._handle_collected_headers(processed_lines, consecutive_headers_info)

        return processed_lines

    def _handle_collected_headers(self,
                                  lines: List[str],
                                  headers_info: List[Tuple[int, int, str]]):
        """
        根据收集到的连续标题信息和处理模式修改行列表。

        Args:
            lines: 要修改的完整行列表。
            headers_info: 收集到的连续同级标题信息列表 [(line_index, level, original_line), ...]。
        """
        if len(headers_info) >= self.min_consecutive_headers:
            level = headers_info[0][1] # 获取这组连续标题的级别
            logging.info(
                f"检测到 {len(headers_info)} 个连续的 {level} 级标题 "
                f"(从行 {headers_info[0][0]+1} 开始，模式: {self.processing_mode})."
            )

            start_index = 0
            if self.processing_mode == 1:
                start_index = 1 # 从第二个标题开始处理
            elif self.processing_mode == 2:
                start_index = 0 # 从第一个标题开始处理
            else:
                logging.warning(f"未知的处理模式: {self.processing_mode}。将不进行任何转换。")
                return


            for idx in range(start_index, len(headers_info)):
                line_index, _, original_line = headers_info[idx]
                # 移除 '#' 和紧随其后的空格
                modified_line = re.sub(r'^#+\s*', '', original_line)
                lines[line_index] = modified_line
                logging.info(f"  - 行 {line_index + 1}: 已将标题转换为普通文本。")
        elif headers_info:
             logging.debug(f"连续 {headers_info[0][1]} 级标题数量 ({len(headers_info)}) 不足 {self.min_consecutive_headers}，不处理。")


def main():
    console.print(Panel(
        Text.from_markup("[bold green]Markdown 连续标题处理器[/bold green]"),
        title="[yellow]欢迎[/yellow]",
        expand=False
    ))
    path = Path(__file__).parent 
    input_path_str = Prompt.ask("请输入 Markdown 文件路径或包含 .md 文件的目录路径", default=str(path))

    output_path_str = Prompt.ask(
        "请输入输出文件或目录的路径 (可选，如果留空：输入为文件则覆盖，输入为目录则在原位修改)",
        default=None,
        show_default=False # 不显示 None 作为默认值提示
    )

    min_consecutive_headers = IntPrompt.ask(
        "触发处理的最小连续同级标题数",
        default=2
    )
    max_blank_lines = IntPrompt.ask(
        "允许连续标题之间存在的最大空行数",
        default=1
    )
    levels_str = Prompt.ask(
        "要处理的标题级别列表，用逗号分隔 (例如 '2,3,4')，留空则处理所有级别 (1-6)",
        default="",
        show_default=False
    )
    processing_mode = IntPrompt.ask(
        "请选择处理模式：\n"
        "1: 从第二个连续标题开始转换\n"
        "2: 从第一个连续标题开始转换",
        choices=["1", "2"],
        default=1
    )
    verbose = Confirm.ask("启用详细日志记录 (DEBUG 级别)？", default=False)

    # 配置日志记录器
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s", # RichHandler 会处理时间戳和级别
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)]
    )
    
    # 打印脚本信息
    console.print(Panel(
        Text.from_markup(
            "[bold green]Markdown 连续标题处理器[/bold green]\n\n"
            f"输入路径: [cyan]{input_path_str}[/cyan]\n"
            f"输出路径: [cyan]{output_path_str or '覆盖原文件/目录'}[/cyan]\n"
            f"处理模式: [cyan]{processing_mode}[/cyan] "
            f"({'从第二个开始' if processing_mode == 1 else '从第一个开始'})"
        ),
        title="[yellow]配置信息[/yellow]",
        expand=False
    ))

    # 解析级别列表
    levels = None
    if levels_str:
        try:
            levels = [int(level.strip()) for level in levels_str.split(',') if level.strip()]
            levels = [lvl for lvl in levels if 1 <= lvl <= 6]
            if not levels:
                logging.warning("指定的级别无效或为空，将处理所有级别。")
                levels = None
        except ValueError:
            logging.error("无法解析级别参数，请使用逗号分隔的数字 (例如 '2,3,4')。将处理所有级别。")
            levels = None

    input_path = Path(input_path_str)
    output_path_arg = Path(output_path_str) if output_path_str else None

    files_to_process: List[Tuple[Path, Path]] = [] # (input_file, output_file)

    if not input_path.exists():
        logging.error(f"错误: 输入路径不存在: {input_path}")
        console.print(f"[bold red]错误: 输入路径不存在: {input_path}[/bold red]")
        exit(1)

    if input_path.is_file():
        if not input_path.suffix.lower() == '.md':
            logging.error(f"错误: 输入文件不是 Markdown 文件: {input_path}")
            console.print(f"[bold red]错误: 输入文件不是 Markdown 文件: {input_path}[/bold red]")
            exit(1)
        
        output_file_path: Path
        if output_path_arg:
            if output_path_arg.is_dir():
                output_file_path = output_path_arg / input_path.name
            else: # output_path_arg is a file
                output_file_path = output_path_arg
        else: # No output_path_arg, overwrite input
            output_file_path = input_path
        files_to_process.append((input_path, output_file_path))

    elif input_path.is_dir():
        if output_path_arg and output_path_arg.is_file():
            logging.error(f"错误: 当输入为目录时，输出路径不能是文件: {output_path_arg}")
            console.print(f"[bold red]错误: 当输入为目录时，输出路径不能是文件: {output_path_arg}[/bold red]")
            exit(1)

        output_base_dir = output_path_arg or input_path # If output_path_arg is None, overwrite in input_dir

        # 确保输出基目录存在（如果指定了新的输出目录）
        if output_base_dir and not output_base_dir.exists() and output_base_dir != input_path :
             output_base_dir.mkdir(parents=True, exist_ok=True)


        logging.info(f"正在扫描目录 [blue]{input_path}[/blue] 中的 Markdown 文件...")
        # 只处理同目录下的md文件，不递归子目录
        md_files = [f for f in input_path.glob("*.md") if f.is_file()]
        if not md_files:
            logging.warning(f"在目录 [blue]{input_path}[/blue] 中未找到 Markdown 文件。")
            console.print(f"[yellow]在目录 {input_path} 中未找到 Markdown 文件。[/yellow]")

        for md_file in md_files:
            # 如果输出目录是输入目录本身（即原地修改），则 output_file_path 就是 md_file
            # 否则，文件将被放置在 output_base_dir 下，保持原文件名
            if output_base_dir == input_path:
                 output_file_path = md_file
            else:
                 output_file_path = output_base_dir / md_file.name
            files_to_process.append((md_file, output_file_path))
    else:
        logging.error(f"错误: 输入路径既不是文件也不是目录: {input_path}")
        console.print(f"[bold red]错误: 输入路径既不是文件也不是目录: {input_path}[/bold red]")
        exit(1)

    processed_count = 0
    error_count = 0

    if not files_to_process:
        console.print("[yellow]没有文件需要处理。[/yellow]")
        exit(0)
        
    console.print(f"\n[bold]开始处理 {len(files_to_process)} 个文件...[/bold]")

    for input_file, output_file in files_to_process:
        console.print(f"处理中: [blue]{input_file}[/blue] -> [green]{output_file}[/green]")
        try:
            # 确保输出文件的父目录存在
            output_file.parent.mkdir(parents=True, exist_ok=True)

            processor = ConsecutiveHeaderProcessor(
                input_path=str(input_file),
                output_path=str(output_file),
                min_consecutive_headers=min_consecutive_headers,
                max_blank_lines_between_headers=max_blank_lines,
                levels_to_process=levels,
                processing_mode=processing_mode
            )
            if processor.process_file():
                processed_count += 1
            else:
                error_count += 1
                console.print(f"[red]处理文件 {input_file} 失败。[/red]")
        except FileNotFoundError as e: # Should be caught by initial checks or processor
            logging.error(f"错误: {e}")
            console.print(f"[bold red]错误: {e}[/bold red]")
            error_count += 1
        except Exception as e:
            logging.exception(f"处理文件 {input_file} 时发生未预料的错误")
            console.print(f"[bold red]处理文件 {input_file} 时发生未预料的错误: {e}[/bold red]")
            error_count += 1
    
    console.print("\n[bold green]处理完成。[/bold green]")
    summary_text = Text()
    summary_text.append(f"成功处理文件数: {processed_count}", style="green")
    if error_count > 0:
        summary_text.append(f"\n失败文件数: {error_count}", style="red")
    else:
        summary_text.append("\n所有文件均成功处理。", style="green")

    console.print(Panel(summary_text, title="[yellow]处理结果[/yellow]", expand=False))

    if error_count > 0:
        exit(1)

if __name__ == '__main__':
    main()