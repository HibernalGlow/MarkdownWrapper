"""连续同级标题处理模块 (重写版)"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import re

from .base import BaseModule, ModuleContext
from .plugins import hookimpl


@dataclass
class _Header:
    index: int
    level: int
    line: str


class ConsecutiveHeaderModule(BaseModule):
    name = "consecutive_header"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        min_consecutive = int(config.get("min_consecutive_headers", 2))
        max_blank = int(config.get("max_blank_lines_between_headers", 1))
        levels = config.get("levels") or config.get("title_levels") or list(range(1, 7))
        mode = int(config.get("processing_mode", 1))  # 1: keep first, 2: drop all markers
        levels = {int(x) for x in levels if 1 <= int(x) <= 6}

        processed = 0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        changed = 0
        verbose = config.get("verbose", True)
        details: list = []
        for file in self._iter_markdown_files(input_path, config):
            text = file.read_text(encoding="utf-8")
            lines = text.splitlines(keepends=True)
            new_lines = self._process(lines, min_consecutive, max_blank, levels, mode)
            modified = self._maybe_write(file, text, "".join(new_lines), dry_run, diffs)
            if modified:
                changed += 1
            if verbose:
                print(f"[consecutive_header] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
            processed += 1
        print(f"[consecutive_header] files={processed} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": processed, "changed": changed, "diffs": diffs, "details": details}


# pluggy 插件入口
@hookimpl
def run(context: ModuleContext, config: Dict[str, Any]):
    mod = ConsecutiveHeaderModule()
    mod.run(context, config)
    return {"ok": True}

    def _get_header(self, line: str) -> Optional[Tuple[int, str]]:
        s = line.strip()
        if not s.startswith('#'):
            return None
        m = re.match(r'^(#+)\s+(.*)$', s)
        if not m:
            return None
        level = len(m.group(1))
        return level, m.group(2)

    def _process(self, lines: List[str], min_consecutive: int, max_blank: int, levels: set[int], mode: int) -> List[str]:
        out = list(lines)
        current: List[_Header] = []
        last_level: Optional[int] = None
        blank = 0

        def flush():
            if len(current) >= min_consecutive:
                start = 1 if mode == 1 else 0
                for h in current[start:]:
                    # remove leading hashes + spaces
                    out[h.index] = re.sub(r'^#+\s*', '', out[h.index])
            current.clear()

        for i, line in enumerate(lines):
            info = self._get_header(line)
            if info and info[0] in levels:
                lvl = info[0]
                if last_level == lvl and blank <= max_blank:
                    current.append(_Header(i, lvl, line))
                else:
                    flush()
                    current = [_Header(i, lvl, line)]
                last_level = lvl
                blank = 0
            else:
                if line.strip() == "":
                    blank += 1
                    if blank > max_blank:
                        flush()
                        last_level = None
                else:
                    flush()
                    last_level = None
                    blank = 0
        flush()
        return out
