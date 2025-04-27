"""
表格处理器模块，处理Markdown表格的格式优化
"""
from ..utils.logger import logger

def remove_empty_table_rows(text):
    """处理表格中的连续空行和首尾空行"""
    lines = text.split('\n')
    result = []
    table_lines = []
    in_table = False
    
    for line in lines:
        # 检查是否是表格行
        if '|' in line:
            if not in_table:
                in_table = True
            table_lines.append(line)
        else:
            if in_table:
                # 处理表格结束
                processed_table = process_table(table_lines)
                result.extend(processed_table)
                table_lines = []
                in_table = False
            result.append(line)
    
    # 处理文件末尾的表格
    if table_lines:
        processed_table = process_table(table_lines)
        result.extend(processed_table)
    
    return '\n'.join(result)

def process_table(table_lines):
    """处理单个表格的行"""
    if not table_lines:
        return []
    
    original_length = len(table_lines)
    # logger.info(f"开始处理表格，原始行数: {original_length}")
    
    # 移除首尾的空行
    while table_lines and is_empty_table_row(table_lines[0]):
        # logger.debug("移除表格首部空行")
        table_lines.pop(0)
    while table_lines and is_empty_table_row(table_lines[-1]):
        # logger.debug("移除表格尾部空行")
        table_lines.pop()
    
    # 处理中间的连续空行和重复行
    result = []
    prev_line = None
    prev_empty = False
    removed_empty = 0
    removed_duplicate = 0
    
    for line in table_lines:
        # 处理空行
        if is_empty_table_row(line):
            if not prev_empty:
                result.append(line)
                prev_empty = True
            else:
                removed_empty += 1
                logger.debug("移除连续空行")
            continue
        
        # 处理重复行
        if line == prev_line:
            removed_duplicate += 1
            logger.debug(f"移除重复行: {line}")
            continue
        
        result.append(line)
        prev_line = line
        prev_empty = False
    
    # logger.info(f"表格处理完成: 移除了 {removed_empty} 个连续空行, {removed_duplicate} 个重复行")
    # logger.info(f"表格行数变化: {original_length} -> {len(result)}")
    return result

def is_empty_table_row(line):
    """检查是否是空的表格行"""
    if not line.strip():
        return True
    parts = line.split('|')[1:-1]  # 去掉首尾的|
    return all(cell.strip() == '' for cell in parts)