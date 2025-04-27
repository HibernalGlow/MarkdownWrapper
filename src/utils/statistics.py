"""
统计模块，用于记录文本处理过程中的各类统计数据
"""
from rich.console import Console
from rich.table import Table
console = Console()
class Statistics:
    """统计类，用于记录文本处理过程中的各类统计数据"""
    def __init__(self):
        self.stats = {
            "processed_files": 0,
            "total_chars_processed": 0,
            "format_changes": 0,
            "pattern_matches": {}
        }
    
    def reset(self):
        """重置所有统计数据"""
        self.__init__()
    
    def increment_processed_files(self):
        """增加已处理文件计数"""
        self.stats["processed_files"] += 1
    
    def add_chars_processed(self, count):
        """增加已处理字符数"""
        self.stats["total_chars_processed"] += count
    
    def increment_format_changes(self):
        """增加格式修改计数"""
        self.stats["format_changes"] += 1
    
    def add_pattern_match(self, pattern_name):
        """记录匹配模式的使用"""
        if isinstance(pattern_name, str) and len(pattern_name) > 50:
            pattern_name = pattern_name[:47] + "..."
        self.stats["pattern_matches"][pattern_name] = self.stats["pattern_matches"].get(pattern_name, 0) + 1

    def get_all_stats(self):
        """获取所有统计数据"""
        return self.stats

    def get_pattern_matches(self):
        """获取模式匹配统计"""
        return self.stats["pattern_matches"]
        
    def print_summary(self):
        """打印统计摘要"""
        all_stats = self.get_all_stats()
        
        table = Table(title="处理统计", show_header=True, header_style="bold magenta")
        table.add_column("指标", style="dim")
        table.add_column("值", justify="right")
        
        table.add_row("处理文件数", str(all_stats["processed_files"]))
        table.add_row("处理字符数", str(all_stats["total_chars_processed"]))
        table.add_row("格式修改次数", str(all_stats["format_changes"]))
        
        console.print(table)
        
        # 显示模式匹配统计
        pattern_matches = self.get_pattern_matches()
        if pattern_matches:
            console.print("\n[bold cyan]替换规则统计:[/bold cyan]")
            pattern_table = Table(show_header=True)
            pattern_table.add_column("规则", style="dim")
            pattern_table.add_column("匹配次数", justify="right")
            
            sorted_patterns = sorted(pattern_matches.items(), key=lambda x: x[1], reverse=True)
            display_count = min(10, len(sorted_patterns))  # 只显示前10个
            
            for pattern, count in sorted_patterns[:display_count]:
                pattern_display = str(pattern)
                pattern_table.add_row(pattern_display, str(count))
            
            if len(pattern_matches) > 10:
                pattern_table.add_row("...", f"还有 {len(pattern_matches) - 10} 项")
                
            console.print(pattern_table)

# 全局统计实例
stats = Statistics()