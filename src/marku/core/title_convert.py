"""标题转换模块 (从 contents_replacer 拆分)

职责: 处理中文数字 / 数字标题规范化，不做其他正文替换。

配置:
  input
  levels: 需要处理的级别 (默认 1-6)
  prompt_levels: 是否交互询问 (默认 False)
  verbose
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import re
import cn2an

from .base import BaseModule, ModuleContext

def _convert_number(m, kind: str):
    if kind in ('number_title','number_subtitle'):
        num = m.group(1)
        return '##### ' + num + '. ' if kind=='number_title' else '###### ' + num + '. '
    chinese = m.group(1)
    special = {'〇':'零','两':'二'}
    chinese = special.get(chinese, chinese)
    try:
        arabic = cn2an.cn2an(chinese, mode='smart')
        standard = cn2an.an2cn(arabic)
    except Exception:
        return m.group(0)
    mapping = {
        'chapter': f'# 第{standard}章 ',
        'section': f'## 第{standard}节 ',
        'subsection': f'### {standard}、',
        'subsubsection': f'#### ({standard}) ',
    }
    return mapping.get(kind, m.group(0))

PATTERNS = {
    1: [(re.compile(r'^第([一二三四五六七八九十百千万零两]+)章(?:\s*)', re.MULTILINE), lambda m: _convert_number(m,'chapter'))],
    2: [(re.compile(r'^第([一二三四五六七八九十百千万零两]+)节(?:\s*)', re.MULTILINE), lambda m: _convert_number(m,'section'))],
    3: [(re.compile(r'^([一二三四五六七八九十百千万零两]+)、(?:\s*)', re.MULTILINE), lambda m: _convert_number(m,'subsection'))],
    4: [(re.compile(r'^\(([一二三四五六七八九十百千万零两]+)\)(?:\s*)', re.MULTILINE), lambda m: _convert_number(m,'subsubsection'))],
    5: [(re.compile(r'^(\d+)\.(?:\s*)', re.MULTILINE), lambda m: _convert_number(m,'number_title'))],
    6: [(re.compile(r'^(\d+\.\d+)\.(?:\s*)', re.MULTILINE), lambda m: _convert_number(m,'number_subtitle'))],
}

class TitleNormalizeModule(BaseModule):
    name = "title_convert"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get('input', context.root))
        levels = config.get('levels') or list(range(1,7))
        levels = [int(x) for x in levels if 1 <= int(x) <= 6]
        prompt = bool(config.get('prompt_levels', False))
        verbose = config.get('verbose', True)
        dry_run = context.shared.get('__dry_run', False)
        if prompt:
            try:
                from rich.prompt import Prompt
                raw = Prompt.ask("标题级别(逗号或范围, 回车默认全部)", default="")
                if raw:
                    lv: List[int] = []
                    for part in raw.split(','):
                        part = part.strip()
                        if '-' in part:
                            a,b = part.split('-',1)
                            lv.extend(range(int(a), int(b)+1))
                        elif part.isdigit():
                            lv.append(int(part))
                    lv = [x for x in lv if 1 <= x <= 6]
                    if lv:
                        levels = sorted(set(lv))
            except Exception:
                pass
        diffs: list = []
        details: list = []
        total=0; changed=0
        for file in self._iter_markdown_files(input_path, config):
            total+=1
            orig = file.read_text(encoding='utf-8')
            new = orig
            for lv in levels:
                for rx, repl in PATTERNS.get(lv, []):
                    new = rx.sub(repl, new)
            modified = self._maybe_write(file, orig, new, dry_run, diffs)
            if modified: changed+=1
            if verbose:
                print(f"[title_convert] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
        print(f"[title_convert] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}
