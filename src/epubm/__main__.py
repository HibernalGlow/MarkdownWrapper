"""EPUB 交叉引用替换工具

功能：
1. 扫描 Markdown 中形如 #html_id#anchor_id 的占位符
2. 从 EPUB 中解析对应 html 文档与 anchor 的元素（或其后第一个兄弟节点）
3. 进行文本替换并输出统计

改进点：
* 单次读写 Markdown（避免多次 IO）
* 使用 Rich 展示进度与结果表格
* Typer CLI：支持多文件、dry-run、输出到新文件
* 提供统计/未解析列表
"""

from __future__ import annotations

import os
import re
from pathlib import Path
import sys
import glob
from typing import Dict, List, Optional, Tuple, TypedDict

import typer
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.table import Table
from rich.panel import Panel
from rich import box
from rich.prompt import Prompt, Confirm
from rich.prompt import Prompt, Confirm


console = Console()
app = typer.Typer(help="EPUB 锚点内容替换到 Markdown 占位符工具")

PLACEHOLDER_PATTERN = re.compile(r"#([\w\-.]+)#([\w\-.]+)")


# --------------------------- 文本规则 --------------------------- #
def preprocess(text: str) -> str:
    """预处理：临时替换避免冲突 (#w -> ￥￥)。"""
    return re.sub(r"#w", "￥￥", text, flags=re.MULTILINE)


def restore(text: str) -> str:
    """恢复预处理标记 (￥￥ -> #w)。"""
    return re.sub(r"￥￥", "#w", text, flags=re.MULTILINE)


# --------------------------- EPUB 解析 --------------------------- #
def extract_html_from_epub(epub_path: Path) -> Dict[str, str]:
    """读取 EPUB 中所有 HTML 资源并返回 {id: html_text}."""
    book = epub.read_epub(str(epub_path))
    html_content: Dict[str, str] = {}
    for item in book.get_items():  # 更稳妥 API
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                html_content[item.get_id()] = item.get_content().decode("utf-8", errors="ignore")
            except Exception as e:  # pragma: no cover - 容错
                console.print(f"[yellow]跳过无法解码项目 {item.get_id()}: {e}")
    return html_content


def build_soup_cache(html_content: Dict[str, str]) -> Dict[str, BeautifulSoup]:
    return {k: BeautifulSoup(v, "html.parser") for k, v in html_content.items()}


def find_anchor(soups: Dict[str, BeautifulSoup], html_id: Optional[str], anchor_id: str) -> Optional[Tuple[str, str]]:
    """查找 anchor 内容.

    返回 (来源 html_id, 替换 HTML 片段) 或 None.
    优先匹配给定 html_id；未找到则全局搜索。
    """
    search_ids: List[str]
    if html_id and html_id in soups:
        search_ids = [html_id]
    else:
        search_ids = list(soups.keys())

    for hid in search_ids:
        soup = soups[hid]
        node = soup.find(id=anchor_id)
        if node:
            # 优先取下一个兄弟；否则取自身；如果有多个连续段落可考虑扩展，这里保持简单
            candidate = node.find_next_sibling() or node
            html_fragment = str(candidate)
            return hid, html_fragment
    return None


# --------------------------- 核心处理 --------------------------- #
class ReplacementResult(TypedDict, total=False):  # type: ignore[misc]
    original: str
    replaced: str
    html_id: str
    anchor_id: str
    source_html: Optional[str]
    success: bool


def process_markdown(md_text: str, soups: Dict[str, BeautifulSoup], dry_run: bool = False) -> Tuple[str, List[ReplacementResult]]:
    results: List[ReplacementResult] = []

    def _replace(match: re.Match) -> str:
        html_id, anchor_id = match.group(1), match.group(2)
        found = find_anchor(soups, html_id, anchor_id)
        if found:
            source, frag = found
            results.append({
                "original": match.group(0),
                "replaced": frag,
                "html_id": html_id,
                "anchor_id": anchor_id,
                "source_html": source,
                "success": True,
            })
            return match.group(0) if dry_run else frag
        else:
            results.append({
                "original": match.group(0),
                "replaced": match.group(0),
                "html_id": html_id,
                "anchor_id": anchor_id,
                "source_html": None,
                "success": False,
            })
            return match.group(0)

    new_text = PLACEHOLDER_PATTERN.sub(_replace, md_text)
    return new_text, results


def summarize(results: List[ReplacementResult]) -> None:
    success = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    table = Table(title="替换结果", box=box.SIMPLE_HEAVY)
    table.add_column("序号", justify="right")
    table.add_column("占位符")
    table.add_column("html id")
    table.add_column("anchor id")
    table.add_column("来源html")
    table.add_column("状态")

    for idx, r in enumerate(results, 1):
        table.add_row(
            str(idx),
            r["original"],
            r["html_id"],
            r["anchor_id"],
            r.get("source_html") or "-",
            "[green]✔ 成功" if r["success"] else "[red]✘ 未找到",
        )

    console.print(table)
    console.print(
        Panel(
            f"总计: {len(results)}  成功: [green]{len(success)}[/]  失败: [red]{len(failed)}[/]",
            title="统计",
            border_style="cyan",
        )
    )

    if failed:
        console.print("[yellow]未解析占位符列表：[/]")
        for r in failed:
            console.print(f"  • {r['original']} (html={r['html_id']}, anchor={r['anchor_id']})")


# --------------------------- CLI 命令 --------------------------- #
def _do_run(md_files: List[Path], epub_path: Path, output_dir: Optional[Path], dry_run: bool, encoding: str) -> None:
    console.rule("[bold cyan]EPUB 引用替换开始")
    if not md_files:
        console.print("[red]未找到任何 Markdown 文件，终止。[/]")
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
        transient=True,
    ) as progress:
        t1 = progress.add_task("读取 EPUB", total=1)
        html_content = extract_html_from_epub(epub_path)
        progress.advance(t1)

        t2 = progress.add_task("解析 Soup", total=1)
        soups = build_soup_cache(html_content)
        progress.advance(t2)

        t_md = progress.add_task("处理 Markdown", total=len(md_files))

        for md_file in md_files:
            progress.update(t_md, description=f"处理 {md_file.name}")
            text = md_file.read_text(encoding=encoding)
            preprocessed = preprocess(text)
            new_text, results = process_markdown(preprocessed, soups, dry_run=dry_run)
            restored = restore(new_text)

            console.rule(f"[bold green]{md_file.name}")
            summarize(results)

            if not dry_run:
                if output_dir:
                    output_dir.mkdir(parents=True, exist_ok=True)
                    target = output_dir / md_file.name
                else:
                    target = md_file
                target.write_text(restored, encoding=encoding)
                console.print(f"[cyan]已写入:[/] {target}")
            else:
                console.print("[yellow]dry-run 模式：未写入文件。")

            progress.advance(t_md)

    console.rule("[bold cyan]完成")


@app.command("run")
def run(
    md_paths: List[Path] = typer.Argument(..., exists=True, readable=True, help="Markdown 文件，可以多个"),
    epub_path: Path = typer.Option(..., "--epub", exists=True, file_okay=True, dir_okay=False, help="EPUB 文件路径"),
    output_dir: Optional[Path] = typer.Option(None, "--out", help="输出目录（不指定则原地覆盖）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅显示替换结果，不写入文件"),
    encoding: str = typer.Option("utf-8", help="Markdown 文件编码"),
):
    """执行占位符替换。"""
    _do_run(md_paths, epub_path, output_dir, dry_run, encoding)


def _expand_markdown_inputs(raw_items: List[str]) -> List[Path]:
    files: List[Path] = []
    for item in raw_items:
        item = item.strip()
        if not item:
            continue
        p = Path(item).expanduser()
        if any(ch in item for ch in ["*", "?", "["]):
            try:
                for g in glob.glob(str(p), recursive=True):
                    gp = Path(g)
                    if gp.is_file() and gp.suffix.lower() == ".md":
                        files.append(gp)
            except Exception as e:
                console.print(f"[yellow]通配符路径错误: {item} - {e}")
            continue
        if p.is_dir():
            try:
                for f in p.rglob("*.md"):
                    files.append(f)
            except Exception as e:
                console.print(f"[yellow]目录扫描错误: {item} - {e}")
        elif p.is_file() and p.suffix.lower() == ".md":
            files.append(p)
        else:
            console.print(f"[yellow]忽略无效路径: {item} (不是 .md 文件或不存在的目录)")
    # 去重 & 排序
    uniq = sorted({f.resolve() for f in files})
    return [Path(u) for u in uniq]


def interactive():
    console.rule("[bold cyan]交互模式 EPUB -> Markdown 替换")
    while True:
        epub_input = Prompt.ask("请输入 EPUB 文件路径 (q 退出)")
        if epub_input.lower() in {"q", "quit", "exit"}:
            console.print("[yellow]退出。")
            return
        epub_input = epub_input.strip('"').strip("'")  # 移除引号
        epub_path = Path(epub_input).expanduser()
        if epub_path.is_file():
            break
        console.print(f"[red]文件不存在: {epub_path}[/]")
        console.print("[yellow]请检查路径是否正确，或输入 'q' 退出。[/]")

    md_raw = Prompt.ask("请输入 Markdown 路径(可: 文件, 目录, 通配符; 多个用逗号)")
    md_items = [x.strip('"').strip("'") for x in md_raw.split(",") if x.strip()]  # 移除引号
    md_files = _expand_markdown_inputs(md_items)
    console.print(f"找到 {len(md_files)} 个 Markdown 文件。")
    if not md_files:
        console.print("[red]未找到 Markdown 文件，结束。[/]")
        return

    out_dir_input = Prompt.ask("输出目录(留空=覆盖原文件)", default="")
    output_dir = Path(out_dir_input).expanduser() if out_dir_input else None
    dry_run = Confirm.ask("是否 dry-run 仅预览?", default=True)
    encoding = Prompt.ask("文件编码", default="utf-8")

    _do_run(md_files, epub_path, output_dir, dry_run, encoding)
    console.print("[green]处理完成。[/]")
    if Confirm.ask("继续再处理一轮?", default=False):
        interactive()


def main():  # 保持向后兼容旧入口方式
    """旧版调用兼容: python -m epubm 仍可运行一个默认示例 (若存在)。"""
    # 若需要可在此提供默认文件；这里仅提示帮助。
    console.print("[bold magenta]请使用命令: python -m epubm run <MD...> --epub <EPUB文件>[/]")
    console.print("示例: python -m epubm run 2.md --epub book.epub")


if __name__ == "__main__":  # noqa: D401
    # 无参数 -> 交互模式；有参数 -> Typer CLI
    if len(sys.argv) == 1:
        try:
            interactive()
        except KeyboardInterrupt:
            console.print("\n[red]用户中断。[/]")
    else:
        app()
