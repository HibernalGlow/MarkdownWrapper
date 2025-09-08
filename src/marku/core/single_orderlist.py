"""孤立单行有序列表处理模块 (重写版)"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any
from .base import BaseModule, ModuleContext


def _process(content: str) -> str:
    lines = content.split('\n')
    rx = re.compile(r'^\s*\d+\.\s')
    flags = [bool(rx.match(l)) for l in lines]
    out = lines[:]
    for i, is_item in enumerate(flags):
        if not is_item:
            continue
        isolated = True
        for j in range(max(0, i-3), i):
            if flags[j]:
                isolated = False
                break
        if isolated:
            for j in range(i+1, min(i+4, len(lines))):
                if flags[j]:
                    isolated = False
                    break
        if isolated:
            out[i] = re.sub(r'(\d+)\.\s', r'\1.', out[i], count=1)
    return '\n'.join(out)


class SingleOrderListModule(BaseModule):
    name = "single_orderlist_remover"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        total = 0
        changed = 0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        verbose = config.get("verbose", True)
        details: list = []
        for file in self._iter_markdown_files(input_path, config):
            total += 1
            text = file.read_text(encoding="utf-8")
            new_text = _process(text)
            modified = self._maybe_write(file, text, new_text, dry_run, diffs)
            if modified:
                changed += 1
            if verbose:
                print(f"[single_orderlist_remover] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
        print(f"[single_orderlist_remover] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}
