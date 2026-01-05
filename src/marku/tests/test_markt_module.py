"""markt 模块测试 - 验证 step.config 配置执行与预期相同"""
import pytest
from pathlib import Path
import tempfile
import shutil

from marku.core.base import ModuleContext
from marku.core.markt_module import MarktModule, headings_to_list, list_to_headings


class TestHeadingsToList:
    """测试标题→列表 (h2l) 核心函数"""

    def test_basic_conversion(self):
        """基础标题转列表"""
        md = "# H1\n## H2\n### H3"
        result = headings_to_list(md)
        assert result == "- H1\n    - H2\n        - H3"

    def test_bullet_style(self):
        """不同列表标记"""
        md = "# Title"
        assert headings_to_list(md, bullet="* ") == "* Title"
        assert headings_to_list(md, bullet="+ ") == "+ Title"

    def test_ordered_list(self):
        """有序列表"""
        md = "# A\n# B\n## B1\n## B2"
        result = headings_to_list(md, ordered=True, ordered_marker=".")
        assert "1. A" in result
        assert "2. B" in result
        assert "1. B1" in result
        assert "2. B2" in result

    def test_max_heading(self):
        """最大标题级别限制"""
        md = "# H1\n## H2\n### H3\n#### H4"
        result = headings_to_list(md, max_heading=2)
        assert "- H1" in result
        assert "    - H2" in result
        assert "H3" not in result
        assert "H4" not in result

    def test_indent_size(self):
        """自定义缩进"""
        md = "# H1\n## H2"
        result = headings_to_list(md, indent_size=2)
        assert result == "- H1\n  - H2"

    def test_max_list_depth(self):
        """最大列表深度限制"""
        md = "# H1\n## H2\n### H3"
        result = headings_to_list(md, max_list_depth=2)
        assert "- H1" in result
        assert "    - H2" in result
        assert "H3" not in result

    def test_code_fence_preserved(self):
        """代码块中的内容不被转换"""
        md = "# Title\n```\n# Not a heading\n```\n## Another"
        result = headings_to_list(md)
        assert "- Title" in result
        assert "# Not a heading" in result
        assert "- Another" in result


class TestListToHeadings:
    """测试列表→标题 (l2h) 核心函数"""

    def test_basic_conversion(self):
        """基础列表转标题"""
        md = "- Item1\n  - Item2\n    - Item3"
        result = list_to_headings(md)
        assert "# Item1" in result
        assert "## Item2" in result
        assert "### Item3" in result

    def test_start_level(self):
        """起始标题级别"""
        md = "- Item1\n  - Item2"
        result = list_to_headings(md, start_level=2)
        assert "## Item1" in result
        assert "### Item2" in result

    def test_max_level(self):
        """最大标题级别限制"""
        md = "- A\n  - B\n    - C\n      - D"
        result = list_to_headings(md, max_level=2)
        assert "# A" in result
        assert "## B" in result
        assert "C" not in result

    def test_ordered_list_input(self):
        """有序列表输入"""
        md = "1. First\n2. Second\n   1. SubItem"
        result = list_to_headings(md)
        assert "# First" in result
        assert "# Second" in result

    def test_code_fence_preserved(self):
        """代码块中的内容不被转换"""
        md = "- Title\n```\n- Not a list\n```\n- Another"
        result = list_to_headings(md)
        assert "# Title" in result
        assert "- Not a list" in result
        assert "# Another" in result


class TestMarktModuleConfig:
    """测试 MarktModule 的 step.config 配置"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d)

    @pytest.fixture
    def sample_md_file(self, temp_dir):
        """创建测试 MD 文件"""
        f = temp_dir / "test.md"
        f.write_text("# Title\n## Subtitle\n### Section", encoding="utf-8")
        return f

    def test_h2l_mode_default(self, temp_dir, sample_md_file):
        """默认 h2l 模式"""
        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "verbose": False})

        result = sample_md_file.read_text(encoding="utf-8")
        assert "- Title" in result
        assert "    - Subtitle" in result

    def test_h2l_mode_with_bullet(self, temp_dir, sample_md_file):
        """h2l 模式自定义 bullet"""
        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "bullet": "* ", "verbose": False})

        result = sample_md_file.read_text(encoding="utf-8")
        assert "* Title" in result

    def test_h2l_mode_ordered(self, temp_dir, sample_md_file):
        """h2l 有序列表模式"""
        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "ordered": True, "verbose": False})

        result = sample_md_file.read_text(encoding="utf-8")
        assert "1. Title" in result

    def test_h2l_mode_indent(self, temp_dir, sample_md_file):
        """h2l 自定义缩进"""
        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "indent": 2, "verbose": False})

        result = sample_md_file.read_text(encoding="utf-8")
        assert "- Title\n  - Subtitle" in result

    def test_h2l_mode_max_heading(self, temp_dir, sample_md_file):
        """h2l 最大标题级别"""
        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "max_heading": 2, "verbose": False})

        result = sample_md_file.read_text(encoding="utf-8")
        assert "- Title" in result
        assert "    - Subtitle" in result
        assert "Section" not in result

    def test_l2h_mode(self, temp_dir):
        """l2h 列表转标题模式"""
        f = temp_dir / "list.md"
        f.write_text("- Item1\n    - Item2\n        - Item3", encoding="utf-8")

        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(f), "mode": "l2h", "indent": 4, "verbose": False})

        result = f.read_text(encoding="utf-8")
        assert "# Item1" in result
        assert "## Item2" in result
        assert "### Item3" in result

    def test_l2h_mode_start_level(self, temp_dir):
        """l2h 起始级别"""
        f = temp_dir / "list.md"
        f.write_text("- A\n    - B", encoding="utf-8")

        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(f), "mode": "l2h", "start_level": 2, "indent": 4, "verbose": False})

        result = f.read_text(encoding="utf-8")
        assert "## A" in result
        assert "### B" in result

    def test_l2h_mode_max_level(self, temp_dir):
        """l2h 最大级别限制"""
        f = temp_dir / "list.md"
        f.write_text("- A\n    - B\n        - C", encoding="utf-8")

        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(f), "mode": "l2h", "max_level": 2, "indent": 4, "verbose": False})

        result = f.read_text(encoding="utf-8")
        assert "# A" in result
        assert "## B" in result
        assert "C" not in result

    def test_dry_run_no_write(self, temp_dir, sample_md_file):
        """dry-run 模式不写入文件"""
        original = sample_md_file.read_text(encoding="utf-8")

        ctx = ModuleContext(root=temp_dir)
        ctx.shared["__dry_run"] = True
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "verbose": False})

        result = sample_md_file.read_text(encoding="utf-8")
        assert result == original
        assert ctx.shared["markt"]["diffs"]  # 有 diff 记录

    def test_context_shared_output(self, temp_dir, sample_md_file):
        """验证 context.shared 输出"""
        ctx = ModuleContext(root=temp_dir)
        mod = MarktModule()
        mod.run(ctx, {"input": str(sample_md_file), "verbose": False})

        output = ctx.shared.get("markt")
        assert output is not None
        assert output["files"] == 1
        assert output["changed"] == 1
        assert output["mode"] == "h2l"
