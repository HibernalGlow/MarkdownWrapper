import pytest
import shutil
from pathlib import Path
import os
import sys

# Add src to sys.path if not already there
src_dir = str(Path(__file__).resolve().parent.parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from marku.scripts.missing_image_remover import remove_missing_images
from marku.core.missing_image import MissingImageModule
from marku.core.base import ModuleContext

TEST_MD_PATH = Path("d:/1VSCODE/Projects/MarkdownAll/MarkdownWrapper/src/marku/scripts/1.md")

def test_missing_image_script_function():
    if not TEST_MD_PATH.exists():
        pytest.skip("Test file 1.md not found")
        
    content = TEST_MD_PATH.read_text(encoding="utf-8")
    base_dir = str(TEST_MD_PATH.parent)
    
    # Since the images are likely not present in the reported absolute paths (on this machine), 
    # they should be detected as missing.
    new_content, removed_count = remove_missing_images(content, base_dir, check_file_uri=True, check_relative=False)
    
    print(f"\nRemoved {removed_count} images via script function.")
    assert removed_count > 0, "Expected at least one missing image to be removed."
    # check that new_content is smaller
    assert len(new_content) < len(content)


def test_missing_image_pipeline_module(tmp_path):
    if not TEST_MD_PATH.exists():
        pytest.skip("Test file 1.md not found")
        
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "1.md"
    shutil.copy(TEST_MD_PATH, test_file)
    
    context = ModuleContext(root=str(test_dir), shared={})
    mod = MissingImageModule()
    
    config = {
        "input": str(test_dir),
        "check_file_uri": True,
        "check_relative": False,
        "verbose": True
    }
    
    mod.run(context, config)
    
    assert "missing_image_remover" in context.shared
    stats = context.shared["missing_image_remover"]
    print(f"\nPipeline module stats: {stats}")
    
    assert stats["files"] == 1
    assert stats["changed"] == 1
    assert stats["details"][0]["removed_images"] > 0
