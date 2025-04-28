"""
统计模块，用于收集和显示处理过程中的统计信息
"""
import time
from datetime import datetime

class Statistics:
    """统计类，用于收集和显示统计信息"""
    
    def __init__(self):
        """初始化统计类"""
        self.reset()
        
    def reset(self):
        """重置统计数据"""
        self.stats = {
            "processed_files": 0,
            "total_chars_processed": 0,
            "format_changes": 0,
            "pattern_matches": {},
            "processing_time": 0,
            "start_time": None,
            "end_time": None
        }
        
    def start_timer(self):
        """开始计时"""
        self.stats["start_time"] = time.time()
        
    def stop_timer(self):
        """停止计时"""
        self.stats["end_time"] = time.time()
        self.stats["processing_time"] = self.stats["end_time"] - self.stats["start_time"]
        
    def add_processed_file(self):
        """增加处理文件数"""
        self.stats["processed_files"] += 1
        
    def add_chars_processed(self, chars_count):
        """增加处理字符数"""
        self.stats["total_chars_processed"] += chars_count
        
    def add_format_change(self):
        """增加格式修改次数"""
        self.stats["format_changes"] += 1
        
    def add_pattern_match(self, pattern_name):
        """增加模式匹配次数"""
        self.stats["pattern_matches"][pattern_name] = self.stats["pattern_matches"].get(pattern_name, 0) + 1
        
    def get_statistics(self):
        """获取统计信息"""
        return self.stats
    
    def get_summary(self):
        """获取统计摘要"""
        summary = {
            "processed_files": self.stats["processed_files"],
            "total_chars": self.stats["total_chars_processed"],
            "format_changes": self.stats["format_changes"],
            "pattern_matches_count": sum(self.stats["pattern_matches"].values()),
            "processing_time": self.stats["processing_time"]
        }
        return summary
    
    def get_pattern_stats(self):
        """获取模式匹配统计信息"""
        return self.stats["pattern_matches"]
    
    def format_summary(self):
        """格式化统计摘要为字符串"""
        summary = self.get_summary()
        
        # 计算处理时间
        if summary["processing_time"] > 60:
            time_str = f"{summary['processing_time'] / 60:.2f} 分钟"
        else:
            time_str = f"{summary['processing_time']:.2f} 秒"
            
        # 构建摘要字符串
        result = [
            "===== 处理统计 =====",
            f"处理文件数: {summary['processed_files']}",
            f"处理字符数: {summary['total_chars']}",
            f"格式修改次数: {summary['format_changes']}",
            f"模式匹配次数: {summary['pattern_matches_count']}",
            f"处理时间: {time_str}",
        ]
        
        # 如果有模式匹配记录，添加前10个最常匹配的模式
        pattern_stats = self.get_pattern_stats()
        if pattern_stats:
            result.append("\n最常匹配的模式:")
            sorted_patterns = sorted(pattern_stats.items(), key=lambda x: x[1], reverse=True)
            for i, (pattern, count) in enumerate(sorted_patterns[:10]):
                if i >= 10:
                    break
                # 如果模式名称太长，截断它
                if len(pattern) > 50:
                    pattern_display = f"{pattern[:47]}..."
                else:
                    pattern_display = pattern
                result.append(f"  - {pattern_display}: {count}次")
                
            if len(sorted_patterns) > 10:
                result.append(f"  - 等 {len(sorted_patterns) - 10} 个更多模式...")
                
        return "\n".join(result)
    
# 创建一个全局统计实例
stats = Statistics()