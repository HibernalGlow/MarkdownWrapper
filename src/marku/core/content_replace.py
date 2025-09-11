"""正文内容替换模块 (从 contents_replacer 拆分)

职责: 不做标题数字级别转换，只执行通用清理 / 标点 / 表格 / 基础正则替换。

可配置:
  input: 路径
  include / exclude / recursive: 继承基础遍历
  verbose: 打印每文件
  patterns: 用户追加自定义正则 (list[[pattern, repl]])
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re

from .base import BaseModule, ModuleContext
from .plugins import hookimpl

BASE_PATTERNS: List[tuple[str,str]] = [
    (r'^ ',''),
    (r'(?:\r?\n){3,}', '\n\n'),
    (r'^.*?目\s{0,10}录.*$\n?', ''),
    (r'\（', '('), (r'\）', ')'),
    (r'\「', '['), (r'\」', ']'),
    (r'\【', '['), (r'\】', ']'),
    (r'\．', '.'), (r'\。', '.'),
    (r'\，', ', '), (r'\；', '; '), (r'\：', ': '),
    (r'\！', '!'), (r'\？', '?'),
    (r'""|"', '"'), (r"''|'", "'"),
    (r'([^|])\n\|(.*?\|.*?\|.*?\n)', r'\1\n\n|\2'),
    (r'\|\n([^|])', r'|\n\n\1'),
    (r':(-{1,1000}):', r'\1'),
    (r'</body></html> ', ''), (r'<html><body>', ''),
    (r'\$\\rightarrow\$', '→'), (r'\$\\leftarrow\$', '←'),
    (r'\$=\$', '='), (r'\^', '+'), (r'\$\+\$', '+'), (r'\^\+', '+'),
    (r'\$\\mathrm\{([a-z])\}\$', r'\1'),
    (r'^\[([\u4e00-\u9fa5A-Za-z0-9]+)\]', r'`[\1]`'),
]

def _apply_patterns(text: str, patterns: List[tuple[str,str]]):
    for pat, repl in patterns:
        text_new = re.sub(pat, repl, text, flags=re.MULTILINE)
        text = text_new
    return text

class ContentReplaceModule(BaseModule):
    name = "content_replace"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get('input', context.root))
        verbose = config.get('verbose', True)
        dry_run = context.shared.get('__dry_run', False)
        diffs: list = []
        details: list = []
        user_patterns = config.get('patterns') or []
        patterns: List[tuple[str,str]] = BASE_PATTERNS + [tuple(p) for p in user_patterns if isinstance(p, (list,tuple)) and len(p)==2]
        total=0; changed=0
        for file in self._iter_markdown_files(input_path, config):
            total+=1
            orig = file.read_text(encoding='utf-8')
            new = _apply_patterns(orig, patterns)
            modified = self._maybe_write(file, orig, new, dry_run, diffs)
            if modified: changed+=1
            if verbose:
                print(f"[content_replace] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
        print(f"[content_replace] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}


# pluggy 插件入口
@hookimpl
def run(context: ModuleContext, config: Dict[str, Any]):
    mod = ContentReplaceModule()
    mod.run(context, config)
    return {"ok": True}
