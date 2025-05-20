"""
表格处理转换器：处理表格中的连续空行和重复行
"""
from mko.utils.marko_transformer import BaseMarkoTransformer
from marko.ext.gfm.elements import Table, TableRow, TableCell
import logging

class TableTransformer(BaseMarkoTransformer):
    """表格处理转换器：优化表格结构"""
    
    def __init__(self):
        """初始化表格处理转换器"""
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def render_table(self, element):
        """
        处理表格元素，优化表格结构
        
        Args:
            element: 表格元素
            
        Returns:
            str: 转换后的表格Markdown文本
        """
        self.logger.info("处理表格元素")
        
        # 获取表头行
        header_row = element.head if hasattr(element, 'head') else None
        
        # 获取表格内容行
        rows = element.children if isinstance(element.children, list) else []
        
        # 移除空行和重复行
        cleaned_rows = self._clean_table_rows(rows)
        
        # 如果没有表头和内容，返回空字符串
        if not header_row and not cleaned_rows:
            return ""
        
        # 构建表格Markdown文本
        table_md = []
        
        # 添加表头
        if header_row:
            header_cells = self._render_cells(header_row.children)
            table_md.append(f"| {' | '.join(header_cells)} |")
            
            # 添加表头分隔行
            separators = ['---' for _ in header_row.children]
            table_md.append(f"| {' | '.join(separators)} |")
        
        # 添加表格内容
        for row in cleaned_rows:
            cells = self._render_cells(row.children)
            table_md.append(f"| {' | '.join(cells)} |")
        
        # 表格前后添加空行
        return f"\n{''.join(table_md)}\n"
    
    def _clean_table_rows(self, rows):
        """
        清理表格行：移除空行和重复行
        
        Args:
            rows: 表格行列表
            
        Returns:
            list: 清理后的表格行列表
        """
        if not rows:
            return []
        
        # 移除空行
        non_empty_rows = []
        for row in rows:
            if self._is_empty_row(row):
                self.logger.debug("移除空行")
                continue
            non_empty_rows.append(row)
        
        # 移除重复行
        cleaned_rows = []
        prev_row_content = None
        
        for row in non_empty_rows:
            curr_row_content = self._get_row_content(row)
            if curr_row_content == prev_row_content:
                self.logger.debug("移除重复行")
                continue
            cleaned_rows.append(row)
            prev_row_content = curr_row_content
        
        self.logger.info(f"表格行数：原始 {len(rows)} -> 清理后 {len(cleaned_rows)}")
        return cleaned_rows
    
    def _is_empty_row(self, row):
        """
        检查表格行是否为空
        
        Args:
            row: 表格行
            
        Returns:
            bool: 是否为空行
        """
        if not hasattr(row, 'children') or not row.children:
            return True
            
        for cell in row.children:
            cell_content = self._get_text_content(cell).strip()
            if cell_content:
                return False
        return True
    
    def _get_row_content(self, row):
        """
        获取表格行内容，用于比较行是否重复
        
        Args:
            row: 表格行
            
        Returns:
            str: 行内容（所有单元格内容拼接）
        """
        if not hasattr(row, 'children'):
            return ""
            
        cell_contents = []
        for cell in row.children:
            cell_content = self._get_text_content(cell).strip()
            cell_contents.append(cell_content)
        
        return '|'.join(cell_contents)
    
    def _render_cells(self, cells):
        """
        渲染表格单元格
        
        Args:
            cells: 单元格列表
            
        Returns:
            list: 单元格内容列表
        """
        rendered_cells = []
        for cell in cells:
            content = self._get_text_content(cell).strip()
            rendered_cells.append(content)
        return rendered_cells
