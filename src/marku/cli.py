"""Typer CLI: 直接运行单个或多个核心模块，或整条管线。

命令示例:
  marku list                       # 列出注册模块
  marku run consecutive_header -i ./docs --dry-run
  marku run mul content_replace title_convert -i ./docs
  marku pipeline -c marku/marku_pipeline.toml --dry-run
"""
from __future__ import annotations
import typer
from pathlib import Path
from typing import List, Optional
from rich.table import Table
from rich.console import Console

from .core.registry import REGISTRY, create
from .core.base import ModuleContext
from .pipeline import PipelineLoader, PipelineExecutor

app = typer.Typer(add_completion=False, help="marku modular markdown toolkit")
console = Console()


def _inject_input(config: dict, input_path: Path):
    if not config.get("input"):
        config["input"] = str(input_path)


@app.command()
def list():
    """列出所有可用模块 (registry 名称)。"""
    table = Table(title="Registered Modules")
    table.add_column("Name", style="cyan")
    table.add_column("Class")
    for name, cls in REGISTRY.items():
        table.add_row(name, cls.__name__)
    console.print(table)


@app.command()
def run(
    module: str = typer.Argument(..., help="模块注册名"),
    input: Path = typer.Option(Path("."), "-i", "--input", help="文件或目录 (默认为当前目录)"),
    include: List[str] = typer.Option([], help="包含模式, 可多次使用"),
    exclude: List[str] = typer.Option([], help="排除模式, 可多次使用"),
    recursive: bool = typer.Option(False, help="递归查找 *.md"),
    dry_run: bool = typer.Option(False, help="干运行: 不写文件, 收集 diff"),
    verbose: bool = typer.Option(True, help="显示每文件状态"),
):
    """运行单个核心模块 (不依赖 pipeline)。"""
    if module not in REGISTRY:
        raise typer.BadParameter(f"未注册模块: {module}")
    ctx = ModuleContext(root=Path.cwd())
    if dry_run:
        ctx.shared['__dry_run'] = True
    mod = create(module)
    config = {
        "input": str(input),
        "include": include or None,
        "exclude": exclude or None,
        "recursive": recursive,
        "verbose": verbose,
    }
    mod.run(ctx, config)
    data = ctx.shared.get(module, {})
    if dry_run and data.get("diffs"):
        for d in data["diffs"][:3]:
            console.rule(f"diff: {d['file']}")
            for line in d['diff'][:40]:
                console.print(line.rstrip("\n"))
            if len(d['diff']) > 40:
                console.print("... (截断)")


@app.command("run-mul")
def run_multiple(
    modules: List[str] = typer.Argument(..., help="多个模块名"),
    input: Path = typer.Option(Path("."), "-i", "--input"),
    dry_run: bool = typer.Option(False, help="干运行"),
):
    """按给定顺序运行多个模块 (轻量串行, 不做拓扑/依赖)。"""
    ctx = ModuleContext(root=Path.cwd())
    if dry_run:
        ctx.shared['__dry_run'] = True
    for m in modules:
        if m not in REGISTRY:
            console.print(f"[red]跳过未注册模块: {m}[/red]")
            continue
        console.rule(f"运行模块: {m}")
        mod = create(m)
        mod.run(ctx, {"input": str(input)})


@app.command()
def pipeline(
    config: Path = typer.Option(Path("marku/marku_pipeline.toml"), "-c", "--config", help="管线 TOML 路径"),
    only: Optional[str] = typer.Option(None, help="只执行指定步骤 (逗号分隔)"),
    input: Optional[Path] = typer.Option(None, "-i", "--input", help="全局 input 注入"),
    dry_run: bool = typer.Option(False, help="干运行"),
    report: Optional[Path] = typer.Option(None, help="报告 JSON"),
    no_preview: bool = typer.Option(False, help="跳过预览"),
):
    """执行完整管线 (支持 --only)。"""
    cfg = PipelineLoader.load(str(config))
    if only:
        wanted = {n.strip() for n in only.split(',') if n.strip()}
        cfg.steps = [s for s in cfg.steps if s.name in wanted]
        if not cfg.steps:
            console.print("[red]无匹配步骤，退出[/red]")
            raise typer.Exit(code=1)
    if input:
        abs_input = input.resolve()
        for s in cfg.steps:
            if not s.config.get("input"):
                s.config["input"] = str(abs_input)
    ex = PipelineExecutor(cfg, use_rich=not no_preview, dry_run=dry_run, report_path=str(report) if report else None)
    ex.run()


if __name__ == "__main__":  # pragma: no cover
    app()
