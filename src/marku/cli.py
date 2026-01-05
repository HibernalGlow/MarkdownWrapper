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
from .core import plugins as _plugins

app = typer.Typer(add_completion=False, help="marku modular markdown toolkit")
console = Console()
def _apply_toml_plugin_toggles(config: Path | None):
    if not config:
        return
    try:
        cfg = PipelineLoader.load(str(config))
        pm = _plugins.plugin_registry
        for n in cfg.plugin_enabled:
            pm.enable(n)
        for n in cfg.plugin_disabled:
            pm.disable(n)
    except Exception:
        pass


@app.callback(invoke_without_command=True)
def _entry(
    ctx: typer.Context,
    config: Path = typer.Option(None, "-c", "--config", help="TOML 配置路径(默认使用包内 marku_pipeline.toml)"),
):
    """未提供子命令时，进入富交互向导：预览 -> 输入路径 -> dry-run 选择 -> 执行。"""
    if ctx.invoked_subcommand is not None:
        return
    try:
        from .interactive import _interactive_wizard
        from pathlib import Path as _P
        cfg = config or (_P(__file__).parent / "marku_pipeline.toml")
        _interactive_wizard(str(cfg))
        raise typer.Exit()
    except Exception:
        # 回落到帮助
        typer.echo(ctx.get_help())
        raise typer.Exit()


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
def plugins(
    config: Path = typer.Option(None, "-c", "--config", help="TOML 配置路径(用于应用 [plugins] 开关)"),
):
    """列出已发现的插件及其来源 (builtin / legacy / entry_point)。"""
    table = Table(title="Discovered Plugins")
    table.add_column("Name", style="cyan")
    table.add_column("Enabled", justify="center")
    table.add_column("Source")
    table.add_column("Obj")
    try:
        _plugins.initialize_plugins()
        pm = _plugins.plugin_registry
        _apply_toml_plugin_toggles(config)
        for n in pm.list_plugins():
            obj = pm.get_plugin(n)
            enabled = "✅" if pm.has_plugin(n) and not pm.is_disabled(n) else "❌"
            src = pm.get_origin(n) if hasattr(pm, "get_origin") else "unknown"
            table.add_row(n, enabled, src, str(obj))
    except Exception as e:
        console.print(f"[red]列出插件失败: {e}[/red]")
    console.print(table)


@app.command("plugin-status")
def plugin_status(
    config: Path = typer.Option(None, "-c", "--config", help="TOML 配置路径(用于应用 [plugins] 开关)"),
):
    """显示插件状态（启用/禁用/来源）。"""
    _plugins.initialize_plugins()
    pm = _plugins.plugin_registry
    _apply_toml_plugin_toggles(config)
    table = Table(title="Plugin Status")
    table.add_column("Name", style="cyan")
    table.add_column("Enabled", justify="center")
    table.add_column("Source")
    for item in pm.list_plugins_status():
        table.add_row(item["name"], "✅" if item["enabled"] and not pm.is_disabled(item["name"]) else "❌", item["origin"])
    console.print(table)


@app.command("plugin-disable")
def plugin_disable(name: str = typer.Argument(..., help="插件名")):
    """禁用一个插件（运行时）。"""
    _plugins.initialize_plugins()
    pm = _plugins.plugin_registry
    ok = pm.disable(name)
    if ok:
        console.print(f"[yellow]已禁用插件: {name}[/yellow]")
    else:
        console.print(f"[red]禁用失败或插件不存在: {name}[/red]")


@app.command("plugin-enable")
def plugin_enable(name: str = typer.Argument(..., help="插件名")):
    """启用一个插件（运行时）。"""
    _plugins.initialize_plugins()
    pm = _plugins.plugin_registry
    ok = pm.enable(name)
    if ok:
        console.print(f"[green]已启用插件: {name}[/green]")
    else:
        console.print(f"[red]启用失败或插件不存在: {name}[/red]")


@app.command()
def run(
    module: str = typer.Argument(..., help="模块注册名"),
    input: Path = typer.Option(Path("."), "-i", "--input", help="文件或目录 (默认为当前目录)"),
    include: List[str] = typer.Option([], help="包含模式, 可多次使用"),
    exclude: List[str] = typer.Option([], help="排除模式, 可多次使用"),
    recursive: bool = typer.Option(False, help="递归查找 *.md"),
    dry_run: bool = typer.Option(False, help="干运行: 不写文件, 收集 diff"),
    verbose: bool = typer.Option(True, help="显示每文件状态"),
    enable_undo: bool = typer.Option(True, "--undo/--no-undo", help="启用撤销记录 (默认启用)"),
):
    """运行单个核心模块 (不依赖 pipeline)。"""
    if module not in REGISTRY:
        raise typer.BadParameter(f"未注册模块: {module}")

    ctx = ModuleContext(root=Path.cwd())
    if dry_run:
        ctx.shared['__dry_run'] = True

    # 启用撤销
    if enable_undo and not dry_run:
        from .core.undo_git import GitUndoManager
        # 如果 input 是文件，取其父目录作为仓库根路径
        repo_root = input.parent if input.is_file() else input
        ctx.undo_manager = GitUndoManager(repo_root)
        # 运行前如果 dirty，先自动保存一份
        if ctx.undo_manager.is_dirty():
            ctx.undo_manager.save_state("Auto-save before module run")

    mod = create(module)
    config = {
        "input": str(input),
        "include": include or None,
        "exclude": exclude or None,
        "recursive": recursive,
        "verbose": verbose,
    }
    mod.run(ctx, config)

    # 运行后保存状态作为此模块的提交
    if ctx.undo_manager:
        sha = ctx.undo_manager.save_state(f"run module: {module}")
        if sha:
            console.print(f"[dim]已保存操作记录: {sha[:8]} (可用 'marku undo' 撤销)[/dim]")

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
    include_disabled: bool = typer.Option(False, help="与 --only 搭配: 允许运行被禁用的步骤"),
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
        if include_disabled:
            for s in cfg.steps:
                s.enabled = True
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


@app.command("interactive")
def interactive(
    config: Path = typer.Option(Path("marku/marku_pipeline.toml"), "-c", "--config", help="TOML 配置路径"),
    input: Optional[Path] = typer.Option(None, "-i", "--input", help="默认输入路径 (可在交互中修改)"),
):
    """启动富交互向导：预览 -> 选择步骤(含禁用) -> 输入路径 -> dry-run -> 执行。"""
    from .interactive import _interactive_wizard
    _interactive_wizard(str(config), initial_input=str(input) if input else None)


@app.command()
def undo(
    commit_id: Optional[str] = typer.Argument(None, help="要回滚到的提交 ID (不填则撤销最近一次)"),
):
    """撤销文件修改操作 (Git 版)。"""
    from .core.undo_git import GitUndoManager
    
    # 默认当前目录为仓库根
    mgr = GitUndoManager(Path.cwd())
    
    if commit_id:
        success = mgr.revert_to(commit_id)
    else:
        success = mgr.undo_latest()

    if success:
        console.print("[green]✓ 成功撤销操作[/green]")
    else:
        console.print("[yellow]撤销未执行或未发现可撤销项[/yellow]")


@app.command()
def history(
    limit: int = typer.Option(10, "-n", "--limit", help="显示记录数量"),
):
    """查看 Git 操作历史。"""
    from .core.undo_git import GitUndoManager
    from rich.table import Table

    mgr = GitUndoManager(Path.cwd())
    records = mgr.get_history(limit)

    if not records:
        console.print("[dim]暂无 marku 操作历史[/dim]")
        return

    table = Table(title="Git 操作历史 (marku)")
    table.add_column("Commit ID", style="cyan")
    table.add_column("时间")
    table.add_column("摘要")
    table.add_column("作者")

    for r in records:
        table.add_row(
            r["id"],
            r["time"].strftime("%m-%d %H:%M"),
            r["summary"],
            r["author"]
        )

    console.print(table)
    console.print("[dim]使用 'marku undo <ID>' 恢复到指定版本[/dim]")


@app.command("clear-history")
def clear_history():
    """Git 模式下不支持内置清理，请使用 Git 命令清理。"""
    console.print("[yellow]Git 模式下请使用标准 Git 工具管理历史记录（如 git log, git gc 等）。[/yellow]")


if __name__ == "__main__":  # pragma: no cover
    app()

