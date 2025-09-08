"""marku 包入口: 支持直接执行或单步执行。

用法示例:
  python -m marku                        # 预览 + 交互输入路径后执行全部
  python -m marku --only clean-headers   # 只执行名为 clean-headers 的步骤
  python -m marku --only clean-headers,title-convert --dry-run --input ./docs
  python -m marku --no-preview --dry-run --report report.json
"""
from __future__ import annotations

from pathlib import Path
import sys, argparse


def main():
    from .pipeline import PipelineLoader, PipelineExecutor
    from .pipeline_main import _interactive_preview

    parser = argparse.ArgumentParser(description="marku modular pipeline entry")
    parser.add_argument("-c", "--config", default=str(Path(__file__).parent / "marku_pipeline.toml"), help="TOML 配置路径")
    parser.add_argument("--only", help="仅执行指定步骤(逗号分隔 step.name)")
    parser.add_argument("--dry-run", action="store_true", help="干运行: 不写文件, 输出 diff")
    parser.add_argument("--report", help="执行报告 JSON 输出路径")
    parser.add_argument("--input", help="全局注入 input (未显式配置的步骤) 的文件或目录")
    parser.add_argument("--no-preview", action="store_true", help="跳过启动时配置预览")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_file():
        print("[marku] 未找到配置: ", config_path)
        sys.exit(1)

    if not args.no_preview:
        try:
            _interactive_preview(str(config_path))
        except Exception as e:
            print(f"[marku] 预览失败(忽略): {e}")

    # 输入路径（命令行优先, 否则交互, 再否则默认 scripts）
    input_path = args.input
    if not input_path:
        try:
            from rich.prompt import Prompt
            input_path = Prompt.ask("请输入待处理文件或目录(回车=默认 ./src/marku/scripts)", default="")
        except Exception:
            input_path = input("输入待处理文件或目录(留空=默认 ./src/marku/scripts): ")
    if not input_path:
        input_path = str(Path(__file__).parent / "scripts")

    cfg = PipelineLoader.load(str(config_path))

    # 仅执行指定步骤
    if args.only:
        wanted = {n.strip() for n in args.only.split(',') if n.strip()}
        original = {s.name for s in cfg.steps}
        missing = wanted - original
        if missing:
            print(f"[marku] 警告: 未找到步骤: {', '.join(sorted(missing))}")
        cfg.steps = [s for s in cfg.steps if s.name in wanted]
        if not cfg.steps:
            print("[marku] 无匹配步骤, 退出。")
            return

    abs_input = Path(input_path).resolve()
    for s in cfg.steps:
        if not s.config.get("input"):
            s.config["input"] = str(abs_input)

    executor = PipelineExecutor(cfg, use_rich=True, dry_run=args.dry_run, report_path=args.report)
    executor.run()

if __name__ == "__main__":  # pragma: no cover
    main()
