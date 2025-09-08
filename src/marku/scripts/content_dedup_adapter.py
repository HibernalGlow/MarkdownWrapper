"""Content Dedup 脚本适配器

提供统一 Runner 接口，对原脚本的函数进行复用。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from .content_dedup import deduplicate_titles, deduplicate_images


class ContentDedupRunner:
    def run(self, context, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        dedup_titles = bool(config.get("dedup_titles", True))
        dedup_images = bool(config.get("dedup_images", False))
        title_levels = config.get("title_levels") or list(range(1, 7))
        if isinstance(title_levels, list):
            title_levels = [int(x) for x in title_levels if 1 <= int(x) <= 6]

        files: List[Path] = []
        if input_path.is_file() and input_path.suffix.lower() == ".md":
            files.append(input_path)
        elif input_path.is_dir():
            files.extend([p for p in input_path.glob("*.md") if p.is_file()])
        else:
            print(f"[content_dedup] 无效输入: {input_path}")
            return

        processed = 0
        for f in files:
            text = f.read_text(encoding="utf-8")
            if dedup_titles:
                text, _ = deduplicate_titles(text, title_levels)
            if dedup_images:
                text, _ = deduplicate_images(text)
            f.write_text(text, encoding="utf-8")
            processed += 1
        print(f"[content_dedup] 处理完成: {processed}/{len(files)}")


Runner = ContentDedupRunner

__all__ = ["ContentDedupRunner", "Runner"]
