#!/usr/bin/env python3
"""
marku 验证脚本

验证 marku 管线的核心功能：
- 配置加载
- 模块注册表
- 步骤执行顺序
- 依赖解析
- 错误处理
- dry-run 模式
- 彩色输出
"""

import sys
import os
from pathlib import Path
import tempfile
import json
from typing import Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.marku.pipeline import PipelineLoader, PipelineExecutor
from src.marku.core.registry import REGISTRY


def create_test_config() -> str:
    """创建测试用的 TOML 配置"""
    config_content = """
[pipeline]
enable = true
root = "./"
sequence = ["consecutive_header", "content_dedup", "html2sy_table"]
global_input = "./test_input.md"

[[step]]
name = "consecutive_header"
enabled = true
module = "consecutive_header"
config.min_consecutive_headers = 2
config.processing_mode = 1

[[step]]
name = "content_dedup"
enabled = true
module = "content_dedup"
config.title_levels = [1, 2, 3]
depends = ["consecutive_header"]

[[step]]
name = "html_table"
enabled = true
module = "html2sy_table"
depends = ["content_dedup"]
"""
    return config_content


def create_test_input() -> str:
    """创建测试输入文件"""
    content = """# 测试文档

## 连续标题1
### 连续标题2
#### 连续标题3

## 另一个标题

<table>
<tr><td>测试表格</td></tr>
</table>

## 重复内容
这是重复的内容。

## 另一个重复内容
这是重复的内容。
"""
    return content


def validate_registry():
    """验证模块注册表"""
    print("🔍 验证模块注册表...")
    expected_modules = [
        "consecutive_header",
        "content_dedup",
        "html2sy_table",
        "image_path_replacer",
        "single_orderlist_remover",
        "t2list",
        "content_replace",
        "title_convert"
    ]

    registered = list(REGISTRY.keys())
    print(f"注册的模块: {registered}")

    missing = [m for m in expected_modules if m not in registered]
    if missing:
        print(f"❌ 缺失模块: {missing}")
        return False

    print("✅ 所有预期模块已注册")
    return True


def validate_config_loading():
    """验证配置加载"""
    print("\n🔍 验证配置加载...")
    try:
        config_content = create_test_config()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        config = PipelineLoader.load(config_path)
        print(f"✅ 配置加载成功: {len(config.steps)} 个步骤")
        print(f"   - 全局输入: {config.global_input}")
        print(f"   - 顺序列表: {config.sequence}")

        # 验证步骤
        for step in config.steps:
            print(f"   - 步骤: {step.name} (模块: {step.module}, 启用: {step.enabled})")
            if step.depends:
                print(f"     依赖: {step.depends}")

        os.unlink(config_path)
        return True

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False


def validate_pipeline_execution():
    """验证管线执行"""
    print("\n🔍 验证管线执行 (dry-run)...")
    try:
        # 创建测试文件
        config_content = create_test_config()
        input_content = create_test_input()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 写入配置
            config_file = temp_path / "test_config.toml"
            config_file.write_text(config_content, encoding='utf-8')

            # 写入输入文件
            input_file = temp_path / "test_input.md"
            input_file.write_text(input_content, encoding='utf-8')

            # 更新配置中的输入路径
            config_content = config_content.replace('./test_input.md', str(input_file).replace('\\', '/'))
            config_file.write_text(config_content, encoding='utf-8')

            # 加载并执行
            config = PipelineLoader.load(config_file)
            executor = PipelineExecutor(config, use_rich=True, dry_run=True)

            print("执行管线...")
            executor.run()

            print("✅ 管线执行完成 (dry-run)")
            return True

    except Exception as e:
        print(f"❌ 管线执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_dependency_resolution():
    """验证依赖解析"""
    print("\n🔍 验证依赖解析...")
    try:
        config_content = """
[pipeline]
enable = true
root = "./"

[[step]]
name = "step1"
enabled = true
module = "consecutive_header"

[[step]]
name = "step2"
enabled = true
module = "content_dedup"
depends = ["step1"]

[[step]]
name = "step3"
enabled = true
module = "html_table"
depends = ["step2"]
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        config = PipelineLoader.load(config_path)
        executor = PipelineExecutor(config, use_rich=False, dry_run=True)

        # 测试依赖解析
        ordered_steps = executor._resolve_order(config.steps)
        step_names = [s.name for s in ordered_steps]

        print(f"解析后的执行顺序: {step_names}")

        # 验证顺序正确性
        step1_idx = step_names.index("step1")
        step2_idx = step_names.index("step2")
        step3_idx = step_names.index("step3")

        if step1_idx < step2_idx < step3_idx:
            print("✅ 依赖顺序正确")
            result = True
        else:
            print("❌ 依赖顺序错误")
            result = False

        os.unlink(config_path)
        return result

    except Exception as e:
        print(f"❌ 依赖解析失败: {e}")
        return False


def main():
    """主验证函数"""
    print("🚀 开始 marku 验证测试\n")

    results = []

    # 运行各项验证
    results.append(("模块注册表", validate_registry()))
    results.append(("配置加载", validate_config_loading()))
    results.append(("依赖解析", validate_dependency_resolution()))
    results.append(("管线执行", validate_pipeline_execution()))

    # 输出结果摘要
    print("\n" + "="*50)
    print("📊 验证结果摘要:")

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {test_name}: {status}")
        if success:
            passed += 1

    print(f"\n总体结果: {passed}/{total} 项通过")

    if passed == total:
        print("🎉 所有验证通过！marku 管线运行正常。")
        return 0
    else:
        print("⚠️  部分验证失败，请检查上述错误信息。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
