"""图片路径替换模块 (重写版)"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any
from .base import BaseModule, ModuleContext


class ImagePathModule(BaseModule):
    name = "image_path_replacer"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        pattern = str(config.get("relative_pattern", "images/"))
        base_url = str(config.get("base_url", ""))
        if not base_url:
            print("[image_path_replacer] base_url 为空，跳过")
            return
        esc = re.escape(pattern)
        rx = re.compile(fr'!\[(.*?)\]\(({esc}[^)]+)\)')
        changed = 0
        total = 0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        verbose = config.get("verbose", True)
        details: list = []
        for file in self._iter_markdown_files(input_path, config):
            total += 1
            text = file.read_text(encoding="utf-8")
            def repl(m):
                rel = m.group(2)
                suffix = rel[len(pattern):]
                return f"![{m.group(1)}]({base_url}{suffix})"
            new_text = rx.sub(repl, text)
            modified = self._maybe_write(file, text, new_text, dry_run, diffs)
            if modified:
                changed += 1
            if verbose:
                print(f"[image_path_replacer] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
        print(f"[image_path_replacer] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}
