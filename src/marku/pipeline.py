"""marku 模块化处理管线

提供统一的 TOML 配置驱动的脚本执行机制，解耦 scripts 目录下的各独立脚本。

配置文件示例 (marku_pipeline.toml):

[pipeline]
enable = true                 # 总开关
root = "./"                    # 根目录（可用于相对路径展开）

[[step]]                      # 处理步骤，按出现顺序执行
name = "consecutive_header"   # 内部注册名
enabled = true
module = "marku.scripts.consecutive_header_adapter"  # 适配器模块 (标准化接口)
class = "ConsecutiveHeaderRunner"                   # 可选：执行类，实现 run(context)
config.min_consecutive_headers = 2                   # 自定义参数 (任意键值对)

[[step]]
name = "content_dedup"
enabled = true
module = "marku.scripts.content_dedup_adapter"
class = "ContentDedupRunner"
config.title_levels = [1,2,3,4,5,6]

运行时，管线为每个 step 构造一个上下文对象并调用其 run()。

为了避免直接修改原始脚本的大量交互/命令行逻辑，这里通过“适配器”层包装。
若后续逐步重构原脚本，可让脚本本身暴露一个纯函数 API，适配器仅做薄封装。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import importlib
import traceback
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


@dataclass
class StepConfig:
    name: str                 # 逻辑名称
    enabled: bool             # 是否启用
    module: str               # 模块名称或 python 模块路径
    clazz: Optional[str] = None  # 可选类名
    config: Dict[str, Any] = field(default_factory=dict)
    order: Optional[int] = None   # 数值排序 (越小越先)
    after: List[str] = field(default_factory=list)   # 需位于这些模块之后
    before: List[str] = field(default_factory=list)  # 需位于这些模块之前
    depends: List[str] = field(default_factory=list) # 依赖 (同 after)
    skip_on_error: bool = True

@dataclass
class PipelineConfig:
    enable: bool = True
    root: str = "./"
    sequence: List[str] = field(default_factory=list)  # 新增：统一顺序控制列表
    steps: List[StepConfig] = field(default_factory=list)
    global_input: str | None = None  # 新增：全局输入目录/文件 (被 CLI -i 覆盖)


class PipelineContext:
    """运行时上下文。用于步骤间共享数据。"""

    def __init__(self, root: Path):
        self.root = root
        self.shared: Dict[str, Any] = {}


class PipelineLoader:
    @staticmethod
    def load(path: str | Path) -> PipelineConfig:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(f"配置文件不存在: {p}")
        data = tomllib.loads(p.read_text(encoding="utf-8"))

        # 顶层 pipeline
        pipeline_raw = data.get("pipeline", {})
        enable = pipeline_raw.get("enable", True)
        root = pipeline_raw.get("root", "./")
        sequence = pipeline_raw.get("sequence", []) or []
        global_input = pipeline_raw.get("global_input") or pipeline_raw.get("input")
        if not isinstance(sequence, list):  # 容错
            sequence = []

        steps_raw = data.get("step", []) or data.get("steps", [])
        steps: List[StepConfig] = []
        for idx, s in enumerate(steps_raw):
            try:
                steps.append(
                    StepConfig(
                        name=s["name"],
                        enabled=s.get("enabled", True),
                        module=s["module"],
                        clazz=s.get("class"),
                        config=s.get("config", {}),
                        order=s.get("order"),
                        after=s.get("after", []),
                        before=s.get("before", []),
                        depends=s.get("depends", []),
                        skip_on_error=s.get("skip_on_error", True),
                    )
                )
            except KeyError as e:  # 必要字段缺失
                raise ValueError(f"第 {idx+1} 个 step 配置缺失字段: {e}")

        return PipelineConfig(enable=enable, root=root, sequence=sequence, steps=steps, global_input=global_input)


class PipelineExecutor:
    def __init__(self, config: PipelineConfig, use_rich: bool = True, dry_run: bool = False, report_path: str | None = None):
        self.config = config
        self.context = PipelineContext(root=Path(config.root).resolve())
        self.use_rich = use_rich
        self.dry_run = dry_run
        self.report_path = report_path
        if use_rich:
            try:  # 延迟导入
                from rich.console import Console  # type: ignore
                from rich.table import Table  # type: ignore
                from rich.panel import Panel  # type: ignore
                self._console = Console()
                self._rich_Table = Table
                self._rich_Panel = Panel
            except Exception:  # pragma: no cover
                self.use_rich = False
                self._console = None

    def _print(self, msg: str):  # 简化输出
        if self.use_rich and self._console:
            self._console.print(msg)
        else:
            print(msg)

    def run(self):
        if not self.config.enable:
            self._print("[marku.pipeline] 管线已禁用，跳过执行。")
            return
        steps_total = len(self.config.steps)
        if self.dry_run:
            self.context.shared['__dry_run'] = True
        if self.use_rich and self._console:
            table = self._rich_Table(title="Pipeline Steps")
            table.add_column("#", justify="right")
            table.add_column("Name", style="cyan")
            table.add_column("Module")
            table.add_column("Enabled", justify="center")
            table.add_column("Input", overflow="fold")
            for i, s in enumerate(self.config.steps, 1):
                used_input = s.config.get("input") or self.config.global_input or "-"
                table.add_row(str(i), s.name, s.module, "✅" if s.enabled else "❌", used_input)
            self._console.print(self._rich_Panel.fit(table, title="Pipeline 初始化"))
        else:
            self._print(f"[marku.pipeline] 启动管线，共 {steps_total} 个步骤。Root={self.context.root}")

        ordered_steps = self._resolve_order(self.config.steps)
        step_reports: List[Dict[str, Any]] = []
        import time, json, logging
        pipeline_start = time.time()
        for idx, step in enumerate(ordered_steps, 1):
            if not step.enabled:
                self._print(f"[marku.pipeline] 跳过步骤 {idx}: {step.name} (disabled)")
                continue
            header = f"步骤 {idx}/{len(ordered_steps)}: {step.name} -> {step.module}{'.'+step.clazz if step.clazz else ''}"
            effective_input = step.config.get("input") or self.config.global_input
            if not effective_input:
                self._log(logging.WARNING, f"跳过: {step.name} 因为没有提供 input (缺少 step.input 与 global_input) – 可用 -i 或在 TOML [pipeline] 添加 global_input")
                continue
            if self.use_rich and self._console:
                self._console.rule(f"[bold green]{header}")
            else:
                self._print(f"[marku.pipeline] {header}")
            step_start = time.time()
            error = None
            try:
                # 归并输入别名
                self._normalize_step_input(step)
                runner = self._instantiate(step)
                if hasattr(runner, "run"):
                    # 若 step.config 未显式 input 且有 global_input 则注入
                    if (not step.config.get("input")) and self.config.global_input:
                        step.config["input"] = self.config.global_input
                    runner.run(self.context, step.config)
                else:
                    raise AttributeError("runner 缺少 run(context, config) 方法")
            except Exception as e:  # pragma: no cover - 运行期健壮性
                self._print(f"[marku.pipeline] 步骤 {step.name} 失败: {e}\n{traceback.format_exc()}")
                error = str(e)
                if not step.skip_on_error:
                    self._print("[marku.pipeline] 终止: skip_on_error=False")
                    break
            module_data = self.context.shared.get(step.module) or self.context.shared.get(step.name) or {}
            # dry-run diff 预览输出
            if self.dry_run and module_data.get("diffs"):
                diffs = module_data["diffs"]
                if self.use_rich and self._console:
                    from rich.text import Text
                    self._print(f"[marku.pipeline] dry-run: {step.name} 变更文件 {len(diffs)} 个 (显示前 3 个)")
                    for d in diffs[:3]:
                        self._console.rule(f"diff: {d['file']}")
                        shown = 0
                        for line in d['diff']:
                            if shown >= 80:
                                self._print("... (截断)")
                                break
                            style = None
                            if line.startswith('+++') or line.startswith('---'):
                                style = "bold blue"
                            elif line.startswith('@@'):
                                style = "bold magenta"
                            elif line.startswith('+') and not line.startswith('+++'):
                                style = "green"
                            elif line.startswith('-') and not line.startswith('---'):
                                style = "red"
                            elif line.startswith(' '):
                                style = "dim"
                            self._console.print(Text(line.rstrip('\n'), style=style))
                            shown += 1
                else:
                    self._print(f"[marku.pipeline] dry-run: {step.name} 变更文件 {len(diffs)} 个 (显示前 3 个)")
                    for d in diffs[:3]:
                        self._print(f"--- diff: {d['file']}")
                        for line in d['diff'][:30]:
                            self._print(line.rstrip('\n'))
                        if len(d['diff']) > 30:
                            self._print("... (截断)")
            step_reports.append({
                "name": step.name,
                "module": step.module,
                "order": step.order,
                "error": error,
                "data": module_data,
                "elapsed": round(time.time()-step_start, 4)
            })
        if self.use_rich and self._console:
            from rich.json import JSON  # type: ignore
            summary = {"shared_keys": list(self.context.shared.keys()), "dry_run": self.dry_run}
            self._console.print(self._rich_Panel(JSON.from_data(summary), title="执行完成"))
            # 文件变化汇总
            try:
                from rich.table import Table  # type: ignore
                table = Table(title="文件变化详情 (前 50)" if self.dry_run else "文件处理结果 (前 50)")
                table.add_column("Step", style="cyan")
                table.add_column("File", style="green")
                table.add_column("Changed", justify="center")
                table.add_column("Extra", style="magenta")
                rows = 0
                for step_name, data in self.context.shared.items():
                    if not isinstance(data, dict):
                        continue
                    details = data.get("details")
                    if not details:
                        continue
                    for d in details:
                        if rows >= 50:
                            break
                        extra = ""
                        if "tables" in d:
                            extra = f"tables={d['tables']}"
                        table.add_row(step_name, d.get("file","-"), "✅" if d.get("changed") else "", extra)
                        rows += 1
                if rows:
                    self._console.print(table)
            except Exception:
                pass
        else:
            self._print("[marku.pipeline] 管线执行完成。")
        if self.report_path:
            report = {
                "root": str(self.context.root),
                "dry_run": self.dry_run,
                "steps": step_reports,
                "elapsed": round(time.time()-pipeline_start, 4)
            }
            try:
                Path(self.report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                self._print(f"[marku.pipeline] 报告已写入 {self.report_path}")
            except Exception as e:  # pragma: no cover
                self._print(f"[marku.pipeline] 写报告失败: {e}")

    def _instantiate(self, step: StepConfig):
        # 允许使用核心注册表中的名称
        try:
            from .core.registry import create, REGISTRY  # 延迟导入
            if step.module in REGISTRY and not step.clazz:
                return create(step.module)
        except Exception:
            pass
        mod = importlib.import_module(step.module)
        if step.clazz:
            cls = getattr(mod, step.clazz)
            return cls()
        if hasattr(mod, "Runner"):
            return getattr(mod, "Runner")()
        # 尝试模块内唯一 BaseModule 子类
        for attr in dir(mod):
            obj = getattr(mod, attr)
            try:
                from .core.base import BaseModule
                if isinstance(obj, type) and issubclass(obj, BaseModule) and obj is not BaseModule:
                    return obj()
            except Exception:
                pass
        raise AttributeError("无法实例化模块: 未找到合适的 Runner/BaseModule 子类")

    # 拓扑排序 + order/sequence 数值 + 原始顺序
    def _resolve_order(self, steps: List[StepConfig]) -> List[StepConfig]:
        name_map = {s.name: s for s in steps}
        # 仅保留 depends 作为强依赖；忽略 after / before（需求：不需要 after 的依赖）
        edges: Dict[str, Set[str]] = {s.name: set() for s in steps}  # from -> to
        indeg: Dict[str, int] = {s.name: 0 for s in steps}
        for s in steps:
            for dep in set(s.depends):
                if dep not in name_map:
                    print(f"[marku.pipeline] 警告: {s.name} depends 目标不存在: {dep}")
                    continue
                if s.name not in edges[dep]:
                    edges[dep].add(s.name)
        # 计算入度
        indeg = {k: 0 for k in edges}
        for frm, tos in edges.items():
            for t in tos:
                indeg[t] += 1
        # 统一顺序控制：若提供 sequence 列表，则其位置优先，其次原始出现顺序
        if self.config.sequence:
            seq_pos = {name: idx for idx, name in enumerate(self.config.sequence)}
            order_map = {s.name: (seq_pos.get(s.name, 10_000 + i), i) for i, s in enumerate(steps)}
        else:
            order_map = {s.name: (s.order if s.order is not None else 10_000, i) for i, s in enumerate(steps)}
        ready = [name for name, d in indeg.items() if d == 0]
        ready.sort(key=lambda n: order_map[n])
        result: List[str] = []
        while ready:
            n = ready.pop(0)
            result.append(n)
            for m in edges[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    ready.append(m)
            ready.sort(key=lambda x: order_map[x])
        if len(result) != len(steps):
            cycle = [n for n, d in indeg.items() if d > 0]
            raise RuntimeError(f"检测到依赖环: {cycle}")
        # 若 sequence 列表存在且没有依赖冲突，可按照 sequence 对结果二次稳定排序（仅对出现的子集）
        if self.config.sequence:
            seq_index = {name: idx for idx, name in enumerate(self.config.sequence)}
            result.sort(key=lambda n: (seq_index.get(n, 10_000), order_map[n]))
        return [name_map[n] for n in result]

    def _normalize_step_input(self, step: StepConfig):
        """归并可能的别名到 step.config['input']。
        优先顺序: 显式 input > 其他别名(path/dir/directory/folder) 第一个非空。
        """
        if step.config.get("input"):
            return
        for k in ("path", "dir", "directory", "folder"):
            v = step.config.get(k)
            if v:
                step.config["input"] = v
                return


def run_pipeline(config_path: str | Path, use_rich: bool = True, dry_run: bool = False, report: str | None = None):
    cfg = PipelineLoader.load(config_path)
    executor = PipelineExecutor(cfg, use_rich=use_rich, dry_run=dry_run, report_path=report)
    executor.run()


__all__ = [
    "PipelineConfig",
    "StepConfig",
    "PipelineLoader",
    "PipelineExecutor",
    "PipelineContext",
    "run_pipeline",
]
