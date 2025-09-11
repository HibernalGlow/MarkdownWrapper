"""命令行入口: 统一执行 marku TOML 管线

使用方式:
  python -m marku.pipeline_main -c path/to/marku_pipeline.toml
或安装后:
  marku-pipeline -c marku/marku_pipeline.toml
"""
from __future__ import annotations

import argparse
from pathlib import Path
from .pipeline import run_pipeline, PipelineLoader, PipelineConfig
from typing import List, Any, Dict, Optional


def _interactive_preview(config_path: str) -> None:
  """仅预览配置，不手动内嵌编辑；提示可在 VSCode 中直接修改后再运行。"""
  from rich.console import Console
  from rich.table import Table
  from rich.panel import Panel
  from rich.prompt import Prompt, Confirm
  from rich import box

  console = Console()
  cfg = PipelineLoader.load(config_path)

  def render():
    table = Table(title=f"Pipeline - {config_path}", box=box.SIMPLE_HEAVY)
    table.add_column("Idx", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Enabled", justify="center")
    table.add_column("Order", justify="right")
    table.add_column("Module", style="magenta")
    table.add_column("After/Depends", style="yellow")
    table.add_column("Config (key=value)")
    for i, s in enumerate(cfg.steps, 1):
      cfg_pairs = ", ".join(f"{k}={v}" for k, v in s.config.items()) if s.config else "-"
      dep_txt = "/".join(s.after or s.depends) if (s.after or s.depends) else "-"
      table.add_row(
        str(i),
        s.name,
        "✅" if s.enabled else "❌",
        str(s.order) if s.order is not None else "-",
        s.module,
        dep_txt,
        cfg_pairs
      )
    console.print(table)

  # 仅展示一次列表
  console.rule("当前管线配置预览")
  for _ in range(1):
    table = Table(title=f"Pipeline - {config_path}", box=box.SIMPLE_HEAVY)
    table.add_column("Idx", justify="right")
    table.add_column("Name", style="cyan")
    table.add_column("Enabled", justify="center")
    table.add_column("Order", justify="right")
    table.add_column("Module", style="magenta")
    table.add_column("Includes", style="green")
    table.add_column("Excludes", style="red")
    for i, s in enumerate(cfg.steps, 1):
      inc = s.config.get('include') or s.config.get('includes') or '-'
      exc = s.config.get('exclude') or s.config.get('excludes') or '-'
      table.add_row(str(i), s.name, "✅" if s.enabled else "❌", str(s.order) if s.order else '-', s.module, str(inc), str(exc))
    console.print(table)
  console.print("[yellow]如需修改，请直接在 VSCode 中编辑该 TOML 文件后重新运行。[/yellow]")

  # 预览后直接返回
  return


def _interactive_wizard(config_path: str, initial_input: Optional[str] = None) -> None:
  """交互式向导：预览配置 -> 输入路径 -> 选择是否 dry-run -> 执行。"""
  from rich.console import Console
  from rich.table import Table
  from rich.panel import Panel
  from rich.prompt import Prompt, Confirm
  from rich import box

  console = Console()
  cfg = PipelineLoader.load(config_path)

  # 预览
  console.rule("当前管线配置预览")
  table = Table(title=f"Pipeline - {config_path}", box=box.SIMPLE_HEAVY)
  table.add_column("Idx", justify="right")
  table.add_column("Name", style="cyan")
  table.add_column("Enabled", justify="center")
  table.add_column("Order", justify="right")
  table.add_column("Module", style="magenta")
  for i, s in enumerate(cfg.steps, 1):
    table.add_row(str(i), s.name, "✅" if s.enabled else "❌", str(s.order) if s.order else '-', s.module)
  console.print(table)

  # 询问输入路径（默认优先 TOML 的 global_input 其次家目录 scripts）
  default_scripts = str(Path(__file__).parent / "scripts")
  default_input = initial_input or cfg.global_input or default_scripts
  input_path = Prompt.ask("请输入待处理文件或目录路径", default=str(default_input) if default_input else default_scripts)
  # dry-run 选择
  dry_run = Confirm.ask("是否以 dry-run 运行 (不写文件, 输出 diff)?", default=False)

  # 选择执行的步骤（支持索引/名称/module，逗号分隔；留空=全部）
  select_raw = Prompt.ask("选择要执行的步骤(逗号分隔, 支持索引/名称/module; 留空=全部)", default="")
  selected_names: set[str] = set()
  if select_raw.strip():
    tokens = [t.strip() for t in select_raw.split(',') if t.strip()]
    by_index = {str(i): s for i, s in enumerate(cfg.steps, 1)}
    by_name = {s.name: s for s in cfg.steps}
    by_module = {s.module: s for s in cfg.steps}
    selected: list = []
    for t in tokens:
      s = by_index.get(t) or by_name.get(t) or by_module.get(t)
      if s:
        selected.append(s)
    if selected:
      selected_names = {s.name for s in selected}
      cfg.steps = [s for s in cfg.steps if s.name in selected_names]
  # 允许运行被禁用的步骤
  include_disabled = False
  if selected_names:
    include_disabled = Confirm.ask("是否允许运行被禁用的步骤(仅对本次所选步骤)?", default=True)
    if include_disabled:
      for s in cfg.steps:
        s.enabled = True

  # 注入 input：仅对未显式配置 input 的步骤
  abs_input = Path(input_path).resolve()
  for s in cfg.steps:
    if not s.config.get("input"):
      s.config["input"] = str(abs_input)

  # 执行
  console.rule("开始执行")
  from .pipeline import PipelineExecutor
  ex = PipelineExecutor(cfg, use_rich=True, dry_run=dry_run, report_path=None)
  ex.run()


def main():
  parser = argparse.ArgumentParser(description="Run marku modular pipeline")
  parser.add_argument("-c", "--config", default=str(Path(__file__).parent / "marku_pipeline.toml"), help="TOML 配置文件路径")
  parser.add_argument("--no-rich", action="store_true", help="禁用 rich 彩色 / 表格输出")
  parser.add_argument("-i", "--interactive", action="store_true", help="仅预览配置并提示在编辑器中修改")
  parser.add_argument("--dry-run", action="store_true", help="干运行：不写文件，输出 diff")
  parser.add_argument("--report", help="执行报告 JSON 输出路径")
  parser.add_argument("-p", "--input", help="全局待处理文件或目录路径 (覆盖未显式配置的 step.config.input)")
  parser.add_argument("--ask-path", action="store_true", help="运行时交互输入路径 (若未提供 --input)")
  parser.add_argument("--only", help="只执行指定步骤 (逗号分隔 step.name 列表)")
  args = parser.parse_args()
  if args.interactive:
    # 进入交互向导：预览 -> 输入路径 -> dry-run 选择 -> 执行
    _interactive_wizard(args.config, initial_input=args.input)
    return
  # 载入配置以便注入路径
  cfg_path = args.config
  from .pipeline import PipelineLoader, PipelineExecutor
  cfg = PipelineLoader.load(cfg_path)
  # 过滤仅执行指定步骤
  if args.only:
    wanted = {n.strip() for n in args.only.split(',') if n.strip()}
    original = {s.name for s in cfg.steps}
    missing = wanted - original
    if missing:
      print(f"[marku.pipeline] 警告: 未找到步骤: {', '.join(sorted(missing))}")
    cfg.steps = [s for s in cfg.steps if s.name in wanted]
    if not cfg.steps:
      print("[marku.pipeline] 未匹配到任何步骤, 退出。")
      return
  # 获取输入路径：命令行优先 -> 交互 -> 默认 scripts 目录
  input_path = args.input
  if not input_path and args.ask_path:
    try:
      from rich.prompt import Prompt
      input_path = Prompt.ask("请输入待处理文件或目录路径(回车使用默认 ./src/marku/scripts)", default="")
    except Exception:
      input_path = input("输入待处理文件或目录路径(留空=默认 ./src/marku/scripts): ")
  if not input_path:
    # 默认包内 scripts 目录
    input_path = str(Path(__file__).parent / "scripts")
  # 标准化为相对/绝对
  input_abs = Path(input_path).resolve()
  # 注入：只有在 step.config 未设置 input 时才填充
  for s in cfg.steps:
    if "input" not in s.config or not s.config.get("input"):
      s.config["input"] = str(input_abs)
  executor = PipelineExecutor(cfg, use_rich=not args.no_rich, dry_run=args.dry_run, report_path=args.report)
  executor.run()


if __name__ == "__main__":  # pragma: no cover
    main()
