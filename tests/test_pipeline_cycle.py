import pytest
from marku.pipeline import PipelineConfig, StepConfig, PipelineExecutor
from pathlib import Path
import tempfile, shutil


def test_cycle_detection():
    tmp = Path(tempfile.mkdtemp())
    try:
        steps = [
            StepConfig(name="a", enabled=True, module="consecutive_header", depends=["c"], config={"input": str(tmp)}),
            StepConfig(name="b", enabled=True, module="content_dedup", depends=["a"], config={"input": str(tmp)}),
            StepConfig(name="c", enabled=True, module="single_orderlist_remover", depends=["b"], config={"input": str(tmp)}),
        ]
        cfg = PipelineConfig(enable=True, root=str(tmp), steps=steps)
        ex = PipelineExecutor(cfg, use_rich=False)
        with pytest.raises(RuntimeError):
            ex._resolve_order(cfg.steps)
    finally:
        shutil.rmtree(tmp)
