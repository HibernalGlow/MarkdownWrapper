import marko
from marko.ext.gfm import gfm  # 导入GFM扩展实例，支持表格
from marko.block import Heading, Paragraph, List, CodeBlock, HTMLBlock, ThematicBreak, Quote
from marko.ext.gfm.elements import Table, TableRow, TableCell
from marko.inline import Link, Image, Emphasis, StrongEmphasis, CodeSpan

# 使用GFM解析器解析Markdown文档
doc = gfm.parse("""
# 主标题

## 副标题

这是一段普通文本，包含**粗体**和*斜体*以及`代码`。

* 无序列表项1
* 无序列表项2
  * 嵌套列表项

1. 有序列表项1
2. 有序列表项2

> 这是一段引用文本
> 多行引用

| 表格 | 示例 |
|------|------|
| 数据1 | 数据2 |
| 数据3 | 数据4 |

---

[链接文本](https://example.com)

![图片描述](https://example.com/image.jpg)

```python
def hello():
    print("Hello, World!")
    return True
```

<div class="custom-class">
  <p>一些HTML内容</p>
</div>
""")

# 辅助函数：显示行内元素的内容
def get_inline_content(element):
    if hasattr(element, 'children'):
        if isinstance(element.children, list):
            return ''.join(str(child) for child in element.children)
        return str(element.children)
    return str(element)

# 遍历并处理不同类型的块
print("===== Markdown 文档结构分析 =====\n")
for i, element in enumerate(doc.children):
    print(f"块 #{i+1}:")
    
    if isinstance(element, Heading):
        print(f"  类型: 标题块 (级别 {element.level})")
        print(f"  内容: {get_inline_content(element)}")
        # 分析标题中的行内元素
        for child in element.children:
            if hasattr(child, 'children'):
                print(f"  行内元素: {type(child).__name__}")
                
    elif isinstance(element, Paragraph):
        print(f"  类型: 段落块")
        print(f"  内容: {get_inline_content(element)}")
        # 分析段落中的行内元素
        for child in element.children:
            if isinstance(child, Link):
                print(f"    - 链接: {child.dest} (文本: {get_inline_content(child)})")
            elif isinstance(child, Image):
                print(f"    - 图片: {child.dest} (描述: {get_inline_content(child)})")
            elif isinstance(child, Emphasis):
                print(f"    - 斜体: {get_inline_content(child)}")
            elif isinstance(child, StrongEmphasis):
                print(f"    - 粗体: {get_inline_content(child)}")
            elif isinstance(child, CodeSpan):
                print(f"    - 行内代码: {child.children}")
                
    elif isinstance(element, List):
        list_type = '有序' if element.ordered else '无序'
        print(f"  类型: {list_type}列表块")
        for j, item in enumerate(element.children):
            item_text = get_inline_content(item.children[0])
            print(f"    - 列表项 {j+1}: {item_text}")
            # 检查嵌套列表
            if len(item.children) > 1:
                for nested_item in item.children[1:]:
                    if isinstance(nested_item, List):
                        nested_type = '有序' if nested_item.ordered else '无序'
                        print(f"      (包含嵌套{nested_type}列表)")
                    elif isinstance(element, Table):
                        print("  类型: 表格块")
        # 显示表头
        if hasattr(element, 'head') and element.head:
            print("  表头行:")
            for cell in element.head.children:
                print(f"    - {get_inline_content(cell)}")
        # 显示表格内容
        print("  表格内容:")
        for i, row in enumerate(element.children):
            print(f"    行 {i+1}:")
            for cell in row.children:
                print(f"      - {get_inline_content(cell)}")
                
    elif isinstance(element, CodeBlock):
        print(f"  类型: 代码块 (语言: {element.lang or '未指定'})")
        print(f"  内容:\n{element.children}")
        
    elif isinstance(element, HTMLBlock):
        print(f"  类型: HTML块")
        print(f"  内容: {element.children}")
        
    elif isinstance(element, Quote):
        print(f"  类型: 引用块")
        print(f"  内容: ", end="")
        for child in element.children:
            print(f"{get_inline_content(child)}")
            
    elif isinstance(element, ThematicBreak):
        print(f"  类型: 分隔线")
        
    print()