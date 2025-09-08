"""标题转层级列表模块 (重写版)"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any
from .base import BaseModule, ModuleContext


def _convert(text: str) -> str:
    lines = text.splitlines()
    counters = [0]*6
    stack: list[int] = []
    result = []
    current_indent = 0
    content_indent = 0
    list_block: list[str] = []
    in_list = False
    for line in lines:
        h = re.match(r'^(#{1,6})\s+(.+)$', line)
        lm = re.match(r'^(\s*)(?:\d+\.|\*|-)\s+.+$', line)
        if h:
            if list_block:
                result.extend(list_block); list_block=[]; in_list=False
            lvl = len(h.group(1))
            while stack and stack[-1] >= lvl:
                stack.pop()
            stack.append(lvl)
            current_indent = len(stack)-1
            content_indent = current_indent+1
            counters[current_indent]+=1
            for i in range(current_indent+1,6): counters[i]=0
            indent = '    '*current_indent
            number = f"{counters[current_indent]}."
            content = h.group(2)
            if '**' not in content:
                content = f"**{content}**"
            result.append(f"{indent}{number} {content}")
        elif lm or (in_list and line.strip() and line.startswith('    ')):
            if not in_list:
                in_list=True; list_block=[]
            base = '    '*content_indent
            extra = ' '*(len(line)-len(line.lstrip()))
            list_block.append(base+extra+line.lstrip())
        else:
            if list_block:
                result.extend(list_block); list_block=[]; in_list=False
            result.append(('    '*content_indent)+line if line.strip() else line)
    if list_block:
        result.extend(list_block)
    return '\n'.join(result)


class T2ListModule(BaseModule):
    name = "t2list"
    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        total=0; changed=0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        verbose = config.get("verbose", True)
        details: list = []
        for file in self._iter_markdown_files(input_path, config):
            total += 1
            txt = file.read_text(encoding='utf-8')
            new = _convert(txt)
            modified = self._maybe_write(file, txt, new, dry_run, diffs)
            if modified:
                changed += 1
            if verbose:
                print(f"[t2list] {'CHANGED' if modified else 'ok'} - {file}")
            details.append({"file": str(file), "changed": bool(modified)})
        print(f"[t2list] files={total} changed={changed}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": total, "changed": changed, "diffs": diffs, "details": details}
