"""标题与图片去重模块 (重写版)"""
from __future__ import annotations

import re
from typing import Dict, Any, List
from pathlib import Path

from .base import BaseModule, ModuleContext


def _dedup_titles(content: str, levels: List[int]):
    levels_set = set(levels)
    seen: Dict[int, set] = {}
    out_lines = []
    for line in content.split('\n'):
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            lvl = len(m.group(1))
            if lvl in levels_set:
                norm = m.group(2).strip().lower()
                bucket = seen.setdefault(lvl, set())
                if norm in bucket:
                    continue
                bucket.add(norm)
        out_lines.append(line)
    return '\n'.join(out_lines)


def _dedup_images(content: str):
    pattern = r'!\[(.*?)\]\((.*?)\)'
    seen = set()
    def repl(match):
        url = match.group(2)
        if url in seen:
            return ''
        seen.add(url)
        return match.group(0)
    return re.sub(pattern, repl, content)


class ContentDedupModule(BaseModule):
    name = "content_dedup"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        title_levels = config.get("title_levels") or list(range(1, 7))
        title_levels = [int(x) for x in title_levels if 1 <= int(x) <= 6]
        do_titles = bool(config.get("dedup_titles", True))
        do_images = bool(config.get("dedup_images", False))
        changed = 0
        total = 0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        verbose = config.get("verbose", True)
        details: list = []
        for file in self._iter_markdown_files(input_path, config):
            total += 1
            text = file.read_text(encoding="utf-8")
            orig = text
            if do_titles:
                text = _dedup_titles(text, title_levels)
            if do_images:
                text = _dedup_images(text)
            modified = self._maybe_write(file, orig, text, dry_run, diffs)
            if modified:
                changed += 1
            if verbose:
                print(f"[content_dedup] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
        print(f"[content_dedup] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}
