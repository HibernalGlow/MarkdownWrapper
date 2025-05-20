"""
测试marko标题转换功能
"""
import os
import sys
import marko
from marko.ext.gfm import GFM

# 添加项目根目录到sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# 导入标题转换器
from mko.utils.header_transformer import HeaderTransformer

# 测试标题文本
test_text = """
第一章 简介与概述
这是简介章节的内容。

第二节 背景
这是背景部分的内容。

一、主要内容
这是主要内容部分。

(二) 次要内容
这是次要内容部分。

1. 第一点
这是第一点的内容。

1.1. 第一小点
这是第一小点的内容。

普通段落不应该被转换为标题。
"""

def main():
    """测试标题转换功能"""
    print("=== 原始文本 ===")
    print(test_text)
    print("\n=== 转换后文本 ===")
    
    # 使用marko解析Markdown
    parser = GFM()
    doc = parser.parse(test_text)
    
    # 测试所有级别的标题转换
    transformer = HeaderTransformer()
    result = transformer.render(doc)
    print(result)
    
    # 测试特定级别的标题转换
    print("\n=== 仅转换1-3级标题 ===")
    transformer = HeaderTransformer(header_levels=[1, 2, 3])
    result = transformer.render(doc)
    print(result)
    
    print("\n=== 仅转换4-6级标题 ===")
    transformer = HeaderTransformer(header_levels=[4, 5, 6])
    result = transformer.render(doc)
    print(result)

if __name__ == '__main__':
    main()
