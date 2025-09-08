"""Adapter: wrap original consecutive_header script logic into pipeline runner interface.

This avoids interactive prompts; parameters come from config.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict

from .consecutive_header import ConsecutiveHeaderProcessor

class ConsecutiveHeaderRunner:
    def run(self, context, config: Dict[str, Any]):  # context: PipelineContext
        input_path = config.get("input", "./")
        min_headers = int(config.get("min_consecutive_headers", 2))
        max_blank = int(config.get("max_blank_lines_between_headers", 1))
        levels = config.get("levels") or config.get("levels_to_process")
        if levels:
            levels = [int(x) for x in levels]
        mode = int(config.get("processing_mode", 1))

        p = Path(input_path)
        details = []
        changed_total = 0
        if p.is_file():
            files = [p]
        else:
            # non recursive simple .md listing
            files = [f for f in Path(p).glob('*.md') if f.is_file()]
        for f in files:
            proc = ConsecutiveHeaderProcessor(
                input_path=str(f),
                output_path=str(f),
                min_consecutive_headers=min_headers,
                max_blank_lines_between_headers=max_blank,
                levels_to_process=levels,
                processing_mode=mode,
            )
            before = f.read_text(encoding='utf-8') if f.exists() else ''
            ok = proc.process_file()
            after = f.read_text(encoding='utf-8') if f.exists() else ''
            changed = before != after
            if changed:
                changed_total += 1
            details.append({
                "file": str(f),
                "changed": changed,
            })
        context.shared['consecutive_header'] = {
            "changed_files": changed_total,
            "details": details,
        }
