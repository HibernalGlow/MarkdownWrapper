from __future__ import annotations

import re
from typing import Iterable

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
    indent_size: int = 2,
    ordered: bool = False,
    ordered_marker: str = ".",
) -> str:
    """将 # 标题转为列表。

    bullet: 无序列表标记("- ", "* ", "+ ")
    max_heading: 最大处理的标题级别(1-6)
    indent_size: 每层缩进空格数
    """
    lines = md.splitlines()
    out: list[str] = []
    state = {"fence": False}
    # 有序列表需要逐级计数器
    counters: dict[int, int] = {}
    for ln in lines:
        if _in_code_fence(ln, state):
            out.append(ln)
            continue
        m = _HEADING_RE.match(ln)
        if m:
            level = min(len(m.group(1)), max_heading)
            text = m.group(2).strip()
            indent = " " * indent_size * (level - 1)
            if ordered:
                # 更新计数器：当前级别+1，清除更深层
                counters[level] = counters.get(level, 0) + 1
                # 清除 deeper
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
) -> str:
    """将有序/无序列表按缩进推断为标题。

    start_level: 顶层映射到的标题级别(1-6)
    max_level: 最大标题级别(1-6)
    indent_size: 每层缩进空格数
    """
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
            level = max(1, min(max_level, start_level + depth))
            out.append("#" * level + " " + text)
        else:
            out.append(ln)
    return "\n".join(out)
