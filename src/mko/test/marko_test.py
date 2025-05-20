"""
测试脚本：测试基于marko的Markdown转换功能
"""
import os
import sys
import logging

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入转换器
from markdownwrapper.core.header_transformer import HeaderTransformer
from mko.utils.text_transformer import TextTransformer
from mko.utils.table_transformer import TableTransformer
from mko.utils.code_protector_transformer import CodeProtectorTransformer

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MarkoTest")

# 测试用的Markdown文本
test_markdown = """
# 已有标题

第一章 需要转换为一级标题

第二节 需要转换为二级标题

一、 需要转换为三级标题

(二) 需要转换为四级标题

1. 需要转换为五级标题

1.1. 需要转换为六级标题

这是一段普通文本，包含**粗体**和*斜体*以及`代码`。
我们需要确保代码块不被修改，而其他内容可以被正常处理。
中文标点如，。：；需要转换为英文标点。

表格测试：

| 表头1 | 表头2 |
|------|------|
| 数据1 | 数据2 |
|      |      |
| 数据1 | 数据2 |
| 数据3 | 数据4 |

代码块测试：

```python
def hello():
    print("Hello, World!")
    return True
```

行内代码测试：`import marko`

"""

def test_header_transformer():
    """测试标题转换器"""
    print("\n=== 测试标题转换器 ===")
    header_transformer = HeaderTransformer()
    result = header_transformer.transform(test_markdown)
    
    print("转换结果:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    return result

def test_text_transformer():
    """测试文本格式化转换器"""
    print("\n=== 测试文本格式化转换器 ===")
    text_transformer = TextTransformer()
    result = text_transformer.transform(test_markdown)
    
    print("转换结果:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    return result

def test_table_transformer():
    """测试表格处理转换器"""
    print("\n=== 测试表格处理转换器 ===")
    table_transformer = TableTransformer()
    result = table_transformer.transform(test_markdown)
    
    print("转换结果:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    return result

def test_code_protector():
    """测试代码保护转换器"""
    print("\n=== 测试代码保护转换器 ===")
    code_protector = CodeProtectorTransformer()
    protected = code_protector.transform(test_markdown)
    
    print("保护后的文本:")
    print("-" * 40)
    print(protected)
    print("-" * 40)
    
    restored = code_protector.restore_code_blocks(protected)
    print("恢复后的文本:")
    print("-" * 40)
    print(restored)
    print("-" * 40)
    
    return restored

def test_combined_transformers():
    """测试组合所有转换器"""
    print("\n=== 测试组合所有转换器 ===")
    
    # 1. 保护代码块
    code_protector = CodeProtectorTransformer()
    protected = code_protector.transform(test_markdown)
    
    # 2. 处理表格
    table_transformer = TableTransformer()
    table_processed = table_transformer.transform(protected)
    
    # 3. 处理标题
    header_transformer = HeaderTransformer()
    headers_processed = header_transformer.transform(table_processed)
    
    # 4. 处理文本格式化
    text_transformer = TextTransformer()
    text_processed = text_transformer.transform(headers_processed)
    
    # 5. 恢复代码块
    result = code_protector.restore_code_blocks(text_processed)
    
    print("最终转换结果:")
    print("-" * 40)
    print(result)
    print("-" * 40)
    
    return result

def main():
    """主函数"""
    print("开始测试基于marko的Markdown转换功能...\n")
    
    # 保存原始测试文本，以便对比
    print("原始Markdown文本:")
    print("-" * 40)
    print(test_markdown)
    print("-" * 40)
    
    # 测试各个转换器
    test_header_transformer()
    test_text_transformer()
    test_table_transformer()
    test_code_protector()
    
    # 测试组合所有转换器
    test_combined_transformers()
    
    print("\n所有测试完成!")

if __name__ == "__main__":
    main()
