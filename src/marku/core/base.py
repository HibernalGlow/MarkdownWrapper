"""核心模块基类与通用上下文定义"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict


@dataclass
class ModuleContext:
    root: Path
    shared: Dict[str, Any] = field(default_factory=dict)

    def resolve(self, *parts: str | Path) -> Path:
        return (self.root.joinpath(*parts)).resolve()


import fnmatch
import difflib


class BaseModule:
    """所有模块需要继承的基类。

    约定:
      - run(context, config) 为唯一必须实现的接口
      - 处理文件时尽量纯逻辑，不进行交互输入/阻塞式询问
      - 可向 context.shared 写入本模块输出供后续模块使用
    """

    name: str = "base"

    def run(self, context: ModuleContext, config: Dict[str, Any]):  # pragma: no cover - 由子类实现
        raise NotImplementedError

    # 可选：通用工具
    def _iter_markdown_files(self, path: str | Path, config: Dict[str, Any]):
        p = Path(path)
        include = config.get("include") or config.get("includes") or []
        exclude = config.get("exclude") or config.get("excludes") or []
        recursive = bool(config.get("recursive", False))
        # 标准化为列表
        if isinstance(include, str):
            include = [include]
        if isinstance(exclude, str):
            exclude = [exclude]
        def match_patterns(file: Path) -> bool:
            rel = file.name
            if include:
                if not any(fnmatch.fnmatch(rel, pat) for pat in include):
                    return False
            if exclude and any(fnmatch.fnmatch(rel, pat) for pat in exclude):
                return False
            return True
        if p.is_file() and p.suffix.lower() == ".md":
            if match_patterns(p):
                yield p
            return
        if p.is_dir():
            iterator = p.rglob("*.md") if recursive or any("**" in pat for pat in include) else p.glob("*.md")
            for f in iterator:
                if f.is_file() and match_patterns(f):
                    yield f

    def _maybe_write(self, file: Path, original: str, new_text: str, dry_run: bool, diffs: list):
        if original == new_text:
            return False
        if dry_run:
            diff_lines = list(difflib.unified_diff(
                original.splitlines(True), new_text.splitlines(True),
                fromfile=str(file), tofile=str(file)))
            diffs.append({"file": str(file), "diff": diff_lines[:5000]})  # 防止超大
            return True
        file.write_text(new_text, encoding="utf-8")
        return True
