import re
import os
import argparse
from lxml import etree
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

console = Console()

def convert_html_table_to_markdown(html_table: str) -> str:
    """将HTML表格转换为思源笔记兼容的Markdown表格
    
    Args:
        html_table: HTML表格字符串
        
    Returns:
        转换后的Markdown表格
    """
    # 解析 HTML 表格
    separator_added = True
    parser = etree.HTMLParser()
    try:
        root = etree.fromstring(html_table, parser)
    except etree.XMLSyntaxError as e:
        console.print(f"[bold red]解析HTML出错:[/] {str(e)}")
        return f"解析HTML出错: {str(e)}"
    
    # 获取所有行
    all_trs = root.xpath('//tr')
    
    if all_trs:
        row_num = len(all_trs)
        col_num = 0
        
        # 计算最大列数
        for td in all_trs[0].xpath('./th|./td'):
            col_num += int(td.get('colspan', 1))
        
        # 创建一个二维列表来存放表格数据
        table_data = [['' for _ in range(col_num)] for _ in range(row_num)]
        
        # 用于填充合并单元格的字符串
        empty_data = '{: class=\'fn__none\'}'
        
        # 逐行解析表格
        for r in range(row_num):
            c = 0
            for td in all_trs[r].xpath('./th|./td'):
                gap = 0
                
                row_span = int(td.get('rowspan', 1))
                col_span = int(td.get('colspan', 1))
                
                # 使用 itertext() 获取文本内容
                content = ''.join(td.itertext()).replace('\n', '<br />')
                
                # 确保不会超出当前行的边界
                while c + gap < len(table_data[r]) and table_data[r][c + gap] == empty_data:
                    gap += 1
                
                if row_span == 1 and col_span == 1:
                    if c + gap < len(table_data[r]):
                        table_data[r][c + gap] = content
                else:
                    for i in range(row_span):
                        for j in range(col_span):
                            if r + i < len(table_data) and c + gap + j < len(table_data[r + i]):
                                table_data[r + i][c + gap + j] = empty_data
                    if c + gap < len(table_data[r]):
                        table_data[r][c + gap] = f"{{: colspan='{col_span}' rowspan='{row_span}'}}" + content
                
                c += gap + col_span
        
        # 将数组中的数据组合成 Markdown 表格模板
        template_str = ""
        for r in range(row_num):
            template_str += '|'
            for c in range(col_num):
                template_str += ' ' + table_data[r][c] + ' |'
            template_str += '\n'
            
            # 添加分隔线在表头行之后或第一行之后
            if (r == 0 or (r == 1 and len(root.xpath('//thead/tr')) > 0)) and separator_added == True:
                template_str += '|' + '|'.join([' --- ' for _ in range(col_num)]) + '|\n'
                separator_added = False
        
        return template_str
    else:
        console.print("[bold yellow]警告:[/] 未找到表格")
        return "未找到表格"

def replace_html_tables_with_markdown(filename: str) -> Tuple[int, List[str]]:
    """替换文件中的HTML表格为Markdown表格
    
    Args:
        filename: 要处理的文件名
        
    Returns:
        元组，包含替换的表格数量和错误消息列表
    """
    console.print(f"[bold blue]处理文件:[/] {filename}")
    
    if not os.path.exists(filename):
        console.print(f"[bold red]错误:[/] 文件 {filename} 不存在")
        return 0, [f"文件 {filename} 不存在"]
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
    except Exception as e:
        console.print(f"[bold red]读取文件出错:[/] {str(e)}")
        return 0, [f"读取文件出错: {str(e)}"]
    
    # 替换HTML标签
    content = content.replace('</body></html>', '').replace('<html><body>', '')

    # 查找所有的 HTML 表格
    html_tables = re.findall(r'<table.*?>.*?</table>', content, re.DOTALL)
    count = len(html_tables)
    
    if count == 0:
        console.print("[yellow]未找到HTML表格[/]")
        return 0, []
    
    console.print(f"[green]找到 {count} 个HTML表格[/]")
    errors = []
    
    # 为每一个 HTML 表格生成 Markdown 表格并替换
    for i, html_table in enumerate(html_tables):
        try:
            markdown_table = convert_html_table_to_markdown(html_table)
            content = content.replace(html_table, markdown_table)
            console.print(f"[green]✓[/] 表格 {i+1}/{count} 转换成功")
        except Exception as e:
            error_msg = f"表格 {i+1}/{count} 转换失败: {str(e)}"
            console.print(f"[bold red]✗[/] {error_msg}")
            errors.append(error_msg)

    try:
        # 写入更新后的内容到文件
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
        console.print(Panel(f"[bold green]成功替换 {count-len(errors)}/{count} 个HTML表格[/]", 
                          title="处理完成", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]写入文件出错:[/] {str(e)}")
        errors.append(f"写入文件出错: {str(e)}")
        return count, errors
    
    return count, errors

def process_directory(directory: str, recursive: bool = False) -> Tuple[int, int]:
    """处理目录中的所有.md文件
    
    Args:
        directory: 要处理的目录
        recursive: 是否递归处理子目录
        
    Returns:
        元组，包含处理的文件数和表格数
    """
    console.print(f"[bold blue]处理目录:[/] {directory}")
    
    if not os.path.isdir(directory):
        console.print(f"[bold red]错误:[/] 目录 {directory} 不存在")
        return 0, 0
    
    total_files = 0
    total_tables = 0
    
    for item in os.listdir(directory):
        full_path = os.path.join(directory, item)
        
        if os.path.isfile(full_path) and full_path.lower().endswith('.md'):
            count, _ = replace_html_tables_with_markdown(full_path)
            total_tables += count
            total_files += 1
        elif os.path.isdir(full_path) and recursive:
            files, tables = process_directory(full_path, recursive)
            total_files += files
            total_tables += tables
    
    return total_files, total_tables

def main():
    """主函数，处理命令行参数"""
    parser = argparse.ArgumentParser(description='将HTML表格转换为思源笔记兼容的Markdown表格')
    parser.add_argument('path', nargs='?', default=None, help='要处理的文件或目录路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('-d', '--demo', action='store_true', help='运行演示，处理当前目录下的1.md文件')
    
    args = parser.parse_args()
    
        # 演示模式，处理1.md文件
    
    path = args.path
    if not path and not args.demo:
        # parser.print_help()
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), '1.md')
        replace_html_tables_with_markdown(filename)
        return
    
    if os.path.isdir(path):
        files, tables = process_directory(path, args.recursive)
        console.print(Panel(f"[bold green]共处理了 {files} 个文件，替换了 {tables} 个HTML表格[/]", 
                          title="处理完成", border_style="green"))
    elif os.path.isfile(path):
        replace_html_tables_with_markdown(path)
    else:
        console.print(f"[bold red]错误:[/] 路径 {path} 不存在")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]用户中断，程序已停止[/]")
    except Exception as e:
        console.print(f"[bold red]程序发生错误:[/] {str(e)}")