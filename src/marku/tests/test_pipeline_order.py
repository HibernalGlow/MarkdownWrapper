import tempfile, shutil, textwrap
from pathlib import Path
from marku.pipeline import PipelineConfig, StepConfig, PipelineExecutor, PipelineContext


def build_config(tmp: Path):
    steps = [
        StepConfig(name="a", enabled=True, module="consecutive_header", config={"input": str(tmp)}, order=20),
    StepConfig(name="b", enabled=True, module="content_dedup", config={"input": str(tmp)}, order=10),
        StepConfig(name="c", enabled=True, module="single_orderlist_remover", depends=["b"], config={"input": str(tmp)}, order=30),
    ]
    return PipelineConfig(enable=True, root=str(tmp), steps=steps)


def test_order_and_execution():
    tmp = Path(tempfile.mkdtemp())
    try:
        # 创建一个简单 md 文件
        (tmp / "sample.md").write_text("## 标题\n## 标题\n1. item\n", encoding="utf-8")
        cfg = build_config(tmp)
        ex = PipelineExecutor(cfg, use_rich=False)
        ex.run()
        # 执行后文件仍应存在
        assert (tmp / "sample.md").exists()
    finally:
        shutil.rmtree(tmp)
