import markdown_it
from markdown_it.token import Token
import json

# 创建带有所有插件的解析器
md = markdown_it.MarkdownIt('commonmark', {'html': True})
md.enable(['table'])  # 启用表格支持

# 测试用的Markdown文本
markdown_text = """
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
"""

# 解析Markdown文本
tokens = md.parse(markdown_text)

# 辅助函数：获取token的类型和内容的简洁描述
def get_token_info(token: Token):
    info = {
        "type": token.type,
        "tag": token.tag if token.tag else None,
        "nesting": token.nesting,
        "level": token.level
    }
    
    # 添加特定类型的相关信息
    if token.type == 'heading_open':
        info['level'] = token.markup.count('#')
    elif token.type == 'fence':
        info['language'] = token.info.strip() if token.info else 'none'
        info['content'] = token.content[:50] + '...' if len(token.content) > 50 else token.content
    elif token.type == 'inline':
        info['content'] = token.content[:50] + '...' if len(token.content) > 50 else token.content
        info['children'] = len(token.children) if hasattr(token, 'children') else 0
    elif token.content:
        info['content'] = token.content[:50] + '...' if len(token.content) > 50 else token.content
    
    # 移除None值
    return {k: v for k, v in info.items() if v is not None}

# 分析令牌结构
def analyze_tokens(tokens):
    print("\n===== Markdown-it-py 文档结构分析 =====\n")
    
    i = 0
    while i < len(tokens):
        token = tokens[i]
        
        # 处理标题
        if token.type == 'heading_open':
            level = token.markup.count('#')
            content_token = tokens[i+1]  # 下一个token应该是内联内容
            print(f"标题 (级别 {level}):")
            print(f"  内容: {content_token.content}")
            i += 2  # 跳过内容和结束标签
        
        # 处理段落
        elif token.type == 'paragraph_open':
            content_token = tokens[i+1]  # 下一个token应该是内联内容
            print(f"段落:")
            print(f"  内容: {content_token.content}")
            
            # 分析内联元素
            if hasattr(content_token, 'children') and content_token.children:
                print("  内联元素:")
                
                # 处理内联元素（这里改用迭代方式而不是依赖索引）
                for child in content_token.children:
                    if child.type == 'link_open':
                        # 寻找链接内容
                        link_content = ""
                        href = child.attrs.get('href', '')
                        child_idx = content_token.children.index(child)
                        j = child_idx + 1
                        while j < len(content_token.children) and content_token.children[j].type != 'link_close':
                            if content_token.children[j].type == 'text':
                                link_content += content_token.children[j].content
                            j += 1
                        print(f"    - 链接: {href} (文本: {link_content})")
                    
                    elif child.type == 'image':
                        src = child.attrs.get('src', '')
                        alt = child.attrs.get('alt', '')
                        print(f"    - 图片: {src} (描述: {alt})")
                    
                    elif child.type == 'strong_open':
                        strong_content = ''
                        child_idx = content_token.children.index(child)
                        j = child_idx + 1
                        while j < len(content_token.children) and content_token.children[j].type != 'strong_close':
                            if content_token.children[j].type == 'text':
                                strong_content += content_token.children[j].content
                            j += 1
                        print(f"    - 粗体: {strong_content}")
                    
                    elif child.type == 'em_open':
                        em_content = ''
                        child_idx = content_token.children.index(child)
                        j = child_idx + 1
                        while j < len(content_token.children) and content_token.children[j].type != 'em_close':
                            if content_token.children[j].type == 'text':
                                em_content += content_token.children[j].content
                            j += 1
                        print(f"    - 斜体: {em_content}")
                    
                    elif child.type == 'code_inline':
                        print(f"    - 行内代码: {child.content}")
            
            i += 2  # 跳过内容和结束标签
        
        # 处理列表
        elif token.type == 'bullet_list_open' or token.type == 'ordered_list_open':
            list_type = '有序' if token.type == 'ordered_list_open' else '无序'
            print(f"{list_type}列表:")
            
            # 处理列表内容
            level = token.level
            j = i + 1
            items = []
            nested_lists = {}
            
            while j < len(tokens):
                if tokens[j].type in ['bullet_list_close', 'ordered_list_close'] and tokens[j].level == level:
                    break
                    
                if tokens[j].type == 'list_item_open' and tokens[j].level == level + 1:
                    item_content = ""
                    # 找到项目的内容（通常是下一个inline token）
                    k = j + 1
                    while k < len(tokens):
                        if tokens[k].type == 'inline' and tokens[k].level == level + 3:
                            item_content = tokens[k].content
                            break
                        k += 1
                    
                    items.append(item_content)
                    
                    # 检查嵌套列表
                    k = j + 1
                    while k < len(tokens):
                        if tokens[k].type == 'list_item_close' and tokens[k].level == level + 1:
                            break
                        if tokens[k].type in ['bullet_list_open', 'ordered_list_open'] and tokens[k].level == level + 2:
                            nested_type = '有序' if tokens[k].type == 'ordered_list_open' else '无序'
                            nested_lists[len(items) - 1] = f"(包含嵌套{nested_type}列表)"
                            break
                        k += 1
                j += 1
            
            # 打印列表项目
            for idx, item in enumerate(items):
                nested_info = nested_lists.get(idx, "")
                print(f"  - 项目 {idx+1}: {item} {nested_info}")
            
            # 跳到列表结束
            while i < len(tokens):
                if tokens[i].type in ['bullet_list_close', 'ordered_list_close'] and tokens[i].level == level:
                    break
                i += 1
        
        # 处理引用
        elif token.type == 'blockquote_open':
            print(f"引用块:")
            
            # 寻找引用内容
            quote_content = []
            j = i + 1
            while j < len(tokens):
                if tokens[j].type == 'blockquote_close':
                    break
                if tokens[j].type == 'inline':
                    quote_content.append(tokens[j].content)
                j += 1
            
            for line in quote_content:
                print(f"  {line}")
            
            # 跳到引用结束
            while i < len(tokens):
                if tokens[i].type == 'blockquote_close':
                    break
                i += 1
        
        # 处理表格
        elif token.type == 'table_open':
            print(f"表格:")
            
            # 查找表头
            j = i + 1
            headers = []
            while j < len(tokens):
                if tokens[j].type == 'thead_close':
                    break
                if tokens[j].type == 'inline' and tokens[j].level == 4:  # 表头单元格内容
                    headers.append(tokens[j].content)
                j += 1
            
            if headers:
                print(f"  表头: {headers}")
            
            # 查找表格内容
            rows = []
            j = i + 1
            current_row = []
            
            while j < len(tokens):
                if tokens[j].type == 'table_close':
                    break
                if tokens[j].type == 'tr_open' and tokens[j].level == 2:
                    current_row = []
                elif tokens[j].type == 'tr_close':
                    if current_row:
                        rows.append(current_row[:])
                elif tokens[j].type == 'inline' and tokens[j].level == 4:  # 表格单元格内容
                    current_row.append(tokens[j].content)
                j += 1
            
            # 打印表格内容
            print("  表格内容:")
            for idx, row in enumerate(rows):
                print(f"    行 {idx+1}: {row}")
            
            # 跳到表格结束
            while i < len(tokens):
                if tokens[i].type == 'table_close':
                    break
                i += 1
        
        # 处理代码块
        elif token.type == 'fence':
            language = token.info.strip() if token.info else '未指定'
            print(f"代码块 (语言: {language}):")
            print(f"  内容:\n{token.content}")
        
        # 处理水平分隔线
        elif token.type == 'hr':
            print(f"分隔线")
        
        # 处理HTML块
        elif token.type == 'html_block':
            print(f"HTML块:")
            print(f"  内容: {token.content.strip()}")
        
        i += 1
        print()

# 显示所有令牌的简要信息 
print("令牌列表:")
for i, token in enumerate(tokens):
    print(f"{i:3d}: {get_token_info(token)}")
print("\n" + "-" * 40 + "\n")

# 分析令牌并以更结构化的方式显示
analyze_tokens(tokens)

# 渲染成HTML (可选)
html_output = md.render(markdown_text)
print("\n===== 渲染后的HTML =====")
print(html_output[:200] + "..." if len(html_output) > 200 else html_output)
