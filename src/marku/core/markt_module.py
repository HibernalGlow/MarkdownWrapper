"""markt 标题/列表互转模块 (marku 适配器)"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

from .base import BaseModule, ModuleContext
from .plugins import hookimpl

# ========== markt 核心转换逻辑 ==========
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_RE = re.compile(r"^(?P<indent>\s*)(?P<marker>([-*+]\s+|\d+[.)]\s+))(?P<text>.*)$")


def _in_code_fence(line: str, state: dict) -> bool:
    if line.lstrip().startswith("```") or line.lstrip().startswith("~~~"):
        state["fence"] = not state.get("fence", False)
        return True
    return state.get("fence", False)


def headings_to_list(
    md: str,
    *,
    bullet: str = "- ",
    max_heading: int = 6,
    indent_size: int = 4,
    ordered: bool = False,
    ordered_marker: str = ".",
    max_list_depth: int | None = None,
) -> str:
    """将 # 标题转为列表。"""
    lines = md.splitlines()
    out: list[str] = []
    state = {"fence": False}
    counters: dict[int, int] = {}
    for ln in lines:
        if _in_code_fence(ln, state):
            out.append(ln)
            continue
        m = _HEADING_RE.match(ln)
        if m:
            level = len(m.group(1))
            if level > max_heading:
                continue
            text = m.group(2).strip()
            indent = " " * indent_size * (level - 1)
            if max_list_depth is not None and level > max_list_depth:
                continue
            if ordered:
                counters[level] = counters.get(level, 0) + 1
                for k in list(counters.keys()):
                    if k > level:
                        counters.pop(k, None)
                mark = f"{counters[level]}{ordered_marker} "
                out.append(f"{indent}{mark}{text}")
            else:
                out.append(f"{indent}{bullet}{text}")
        else:
            out.append(ln)
    return "\n".join(out)


def list_to_headings(
    md: str,
    *,
    start_level: int = 1,
    max_level: int = 6,
    indent_size: int = 2,
    max_list_depth: int | None = None,
) -> str:
    """将有序/无序列表按缩进推断为标题。"""
    lines = md.splitlines()
    out: list[str] = []
    state = {"fence": False}
    for ln in lines:
        if _in_code_fence(ln, state):
            out.append(ln)
            continue
        m = _LIST_RE.match(ln)
        if m:
            indent = m.group("indent")
            text = m.group("text").strip()
            depth = len(indent) // indent_size
            if max_list_depth is not None and (depth + 1) > max_list_depth:
                continue
            level = start_level + depth
            if level > max_level:
                continue
            level = max(1, min(6, level))
            out.append("#" * level + " " + text)
        else:
            out.append(ln)
    return "\n".join(out)


# ========== marku 模块适配 ==========
class MarktModule(BaseModule):
    """markt: Markdown 标题 ↔ 列表 互转模块"""

    name = "markt"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        dry_run = context.shared.get("__dry_run", False)
        verbose = config.get("verbose", True)
        diffs: list = []
        details: list = []

        mode = config.get("mode", "h2l")
        bullet = config.get("bullet", "- ")
        max_heading = config.get("max_heading", 6)
        indent_size = config.get("indent", 4)
        ordered = config.get("ordered", False)
        ordered_marker = config.get("ordered_marker", ".")
        max_list_depth = config.get("max_list_depth", None)
        if max_list_depth is not None and max_list_depth <= 0:
            max_list_depth = None
        start_level = config.get("start_level", 1)
        max_level = config.get("max_level", 6)

        files_count = 0
        changed_count = 0

        for file in self._iter_markdown_files(input_path, config):
            files_count += 1
            orig_text = file.read_text(encoding="utf-8")

            if mode == "h2l":
                new_text = headings_to_list(
                    orig_text,
                    bullet=bullet,
                    max_heading=max(1, min(6, int(max_heading))),
                    indent_size=max(1, int(indent_size)),
                    ordered=bool(ordered),
                    ordered_marker=ordered_marker,
                    max_list_depth=max_list_depth,
                )
            else:
                new_text = list_to_headings(
                    orig_text,
                    start_level=max(1, min(6, int(start_level))),
                    max_level=max(1, min(6, int(max_level))),
                    indent_size=max(1, int(indent_size)),
                    max_list_depth=max_list_depth,
                )

            changed = self._maybe_write(file, orig_text, new_text, dry_run, diffs)
            if changed:
                changed_count += 1
                details.append({"file": str(file), "changed": True, "mode": mode})
                if verbose:
                    print(f"[markt] CHANGED mode={mode} - {file}")
            else:
                details.append({"file": str(file), "changed": False, "mode": mode})
                if verbose:
                    print(f"[markt] ok mode={mode} - {file}")

        print(f"[markt] files={files_count} changed={changed_count} mode={mode}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": files_count, "changed": changed_count, "mode": mode, "diffs": diffs, "details": details}


@hookimpl
def run(context: ModuleContext, config: Dict[str, Any]):
    mod = MarktModule()
    mod.run(context, config)
    return {"ok": True}
