"""HTML 表格转换模块 (重写版)"""
from __future__ import annotations

import re
from typing import Any, Dict
from pathlib import Path
from lxml import etree

from .base import BaseModule, ModuleContext
from .plugins import hookimpl


def _convert_table(html_table: str) -> str:
    parser = etree.HTMLParser()
    try:
        root = etree.fromstring(html_table, parser)
    except etree.XMLSyntaxError:
        return html_table  # 保持原样
    rows = root.xpath('//tr')
    if not rows:
        return html_table
    # 计算列数
    col_num = sum(int(td.get('colspan', 1)) for td in rows[0].xpath('./th|./td'))
    row_num = len(rows)
    data = [['' for _ in range(col_num)] for _ in range(row_num)]
    empty_tag = '{: class=\'fn__none\'}'
    for r, tr in enumerate(rows):
        c = 0
        for td in tr.xpath('./th|./td'):
            while c < col_num and data[r][c] == empty_tag:
                c += 1
            rs = int(td.get('rowspan', 1))
            cs = int(td.get('colspan', 1))
            content = ''.join(td.itertext()).replace('\n', '<br />')
            for i in range(rs):
                for j in range(cs):
                    if r + i < row_num and c + j < col_num:
                        data[r + i][c + j] = empty_tag
            data[r][c] = (f"{{: colspan='{cs}' rowspan='{rs}'}}" + content) if (rs > 1 or cs > 1) else content
            c += cs
    out_lines = []
    for r, row in enumerate(data):
        out_lines.append('|' + ' '.join(cell + ' |' for cell in row))
        if r == 0:
            out_lines.append('|' + (' --- |' * col_num))
    return '\n'.join(out_lines) + '\n'


class HtmlTableModule(BaseModule):
    name = "html2sy_table"

    def run(self, context: ModuleContext, config: Dict[str, Any]):
        input_path = Path(config.get("input", context.root))
        total_tables = 0
        files = 0
        dry_run = context.shared.get("__dry_run", False)
        diffs: list = []
        verbose = config.get("verbose", True)
        details: list = []
        for file in self._iter_markdown_files(input_path, config):
            files += 1
            orig_text = file.read_text(encoding="utf-8")
            text = orig_text.replace('</body></html>', '').replace('<html><body>', '')
            tables = re.findall(r'<table.*?>.*?</table>', text, re.DOTALL)
            changed_here = False
            if tables:
                for t in tables:
                    new_t = _convert_table(t)
                    if new_t != t:
                        text = text.replace(t, new_t)
                        changed_here = True
                if changed_here and self._maybe_write(file, orig_text, text, dry_run, diffs):
                    total_tables += len(tables)
                    details.append({"file": str(file), "changed": True, "tables": len(tables)})
                    if verbose:
                        print(f"[html2sy_table] CHANGED tables={len(tables)} - {file}")
                else:
                    details.append({"file": str(file), "changed": False, "tables": len(tables)})
                    if verbose:
                        print(f"[html2sy_table] ok tables={len(tables)} - {file}")
            else:
                details.append({"file": str(file), "changed": False, "tables": 0})
                if verbose:
                    print(f"[html2sy_table] ok tables=0 - {file}")
        print(f"[html2sy_table] files={files} tables_converted={total_tables}{' (dry-run)' if dry_run else ''}")
        context.shared[self.name] = {"files": files, "tables": total_tables, "diffs": diffs, "details": details}


# pluggy 插件入口
@hookimpl
def run(context: ModuleContext, config: Dict[str, Any]):
    mod = HtmlTableModule()
    mod.run(context, config)
    return {"ok": True}
