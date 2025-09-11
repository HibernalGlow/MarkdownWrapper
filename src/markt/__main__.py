from __future__ import annotations

import sys
import argparse
from pathlib import Path
from .convert import headings_to_list, list_to_headings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="markt: Markdown 标题 ↔ 有序/无序列表 互转 (CLI)")
    parser.add_argument("--mode", choices=["h2l", "l2h"], default="h2l", help="h2l=标题→列表, l2h=列表→标题")
    parser.add_argument("-i", "--input", help="输入文件(省略或为 '-' 则读标准输入)")
    parser.add_argument("-o", "--output", help="输出文件(省略则写到标准输出)")
    parser.add_argument("--indent", type=int, default=2, help="每级缩进空格数 (默认2)")
    # 标题→列表
    parser.add_argument("--bullet", default="- ", choices=["- ", "* ", "+ "], help="无序列表标记")
    parser.add_argument("--ordered", action="store_true", help="使用有序列表 (标题→列表)")
    parser.add_argument("--ordered-marker", default=".", choices=[".", ")"], help="有序编号样式")
    parser.add_argument("--max-heading", type=int, default=6, help="最大处理标题级别 1-6 (标题→列表)")
    # 列表→标题
    parser.add_argument("--start-level", type=int, default=1, help="顶层映射到的标题级别 1-6 (列表→标题)")
    parser.add_argument("--max-level", type=int, default=6, help="最大标题级别 1-6 (列表→标题)")
    args = parser.parse_args(argv)

    # 读取输入
    if not args.input or args.input == "-":
        src = sys.stdin.read()
    else:
        src = Path(args.input).read_text(encoding="utf-8")

    if args.mode == "h2l":
        dst = headings_to_list(
            src,
            bullet=args.bullet,
            max_heading=max(1, min(6, int(args.max_heading))),
            indent_size=max(1, int(args.indent)),
            ordered=bool(args.ordered),
            ordered_marker=args.ordered_marker,
        )
    else:
        # l2h
        dst = list_to_headings(
            src,
            start_level=max(1, min(6, int(args.start_level))),
            max_level=max(1, min(6, int(args.max_level))),
            indent_size=max(1, int(args.indent)),
        )

    if args.output:
        Path(args.output).write_text(dst, encoding="utf-8")
    else:
        sys.stdout.write(dst)
        if not dst.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
