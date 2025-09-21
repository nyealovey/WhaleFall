"""
鲸落 - 常量监控器
监控常量使用情况，提供使用统计和变更监控
"""

import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

from app.constants import (
    CacheKeys,
    DangerousPatterns,
    DefaultConfig,
    ErrorMessages,
    FieldLengths,
    LogLevel,
    LogType,
    Pagination,
    RegexPatterns,
    SuccessMessages,
    SyncType,
    SystemConstants,
    TaskStatus,
    TimeFormats,
    UserRole,
)


class ConstantsMonitor:
    """常量监控器"""

    def __init__(self, project_root: str = None):
        """
        初始化常量监控器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = project_root or str(Path(__file__).parent.parent.parent)
        self.app_dir = os.path.join(self.project_root, "app")
        self.usage_stats = defaultdict(int)
        self.change_log = []
        self.constants_snapshot = {}
        self.monitoring_enabled = True

    def track_usage(self, constant_name: str, file_path: str = None, line_number: int = None) -> None:
        """
        跟踪常量使用

        Args:
            constant_name: 常量名称
            file_path: 使用文件路径
            line_number: 使用行号
        """
        if not self.monitoring_enabled:
            return

        self.usage_stats[constant_name] += 1
        
        # 记录详细使用信息
        usage_info = {
            "constant_name": constant_name,
            "file_path": file_path,
            "line_number": line_number,
            "timestamp": datetime.now(),
        }
        
        # 这里可以添加更详细的日志记录
        self._log_usage(usage_info)

    def track_change(self, constant_name: str, old_value: Any, new_value: Any, file_path: str = None) -> None:
        """
        跟踪常量变更

        Args:
            constant_name: 常量名称
            old_value: 旧值
            new_value: 新值
            file_path: 变更文件路径
        """
        if not self.monitoring_enabled:
            return

        change_info = {
            "constant_name": constant_name,
            "old_value": old_value,
            "new_value": new_value,
            "file_path": file_path,
            "timestamp": datetime.now(),
        }
        
        self.change_log.append(change_info)
        self._log_change(change_info)

    def get_usage_stats(self) -> Dict[str, int]:
        """
        获取使用统计

        Returns:
            Dict: 使用统计信息
        """
        return dict(self.usage_stats)

    def get_change_log(self) -> List[Dict[str, Any]]:
        """
        获取变更日志

        Returns:
            List: 变更日志列表
        """
        return self.change_log.copy()

    def get_high_usage_constants(self, threshold: int = 5) -> List[str]:
        """
        获取高频使用常量

        Args:
            threshold: 使用次数阈值

        Returns:
            List: 高频使用常量列表
        """
        return [name for name, count in self.usage_stats.items() if count >= threshold]

    def get_unused_constants(self) -> List[str]:
        """
        获取未使用常量

        Returns:
            List: 未使用常量列表
        """
        all_constants = self._get_all_constants()
        used_constants = set(self.usage_stats.keys())
        return list(set(all_constants) - used_constants)

    def get_constants_by_usage(self) -> Dict[str, List[str]]:
        """
        按使用情况分组常量

        Returns:
            Dict: 按使用情况分组的常量
        """
        result = {
            "high_usage": [],
            "medium_usage": [],
            "low_usage": [],
            "unused": [],
        }
        
        for constant_name, count in self.usage_stats.items():
            if count >= 10:
                result["high_usage"].append(constant_name)
            elif count >= 5:
                result["medium_usage"].append(constant_name)
            elif count > 0:
                result["low_usage"].append(constant_name)
        
        result["unused"] = self.get_unused_constants()
        
        return result

    def generate_usage_report(self) -> Dict[str, Any]:
        """
        生成使用报告

        Returns:
            Dict: 使用报告数据
        """
        total_constants = len(self._get_all_constants())
        used_constants = len(self.usage_stats)
        unused_constants = len(self.get_unused_constants())
        
        return {
            "total_constants": total_constants,
            "used_constants": used_constants,
            "unused_constants": unused_constants,
            "usage_rate": (used_constants / total_constants * 100) if total_constants > 0 else 0,
            "usage_stats": dict(self.usage_stats),
            "change_count": len(self.change_log),
            "high_usage_constants": self.get_high_usage_constants(),
            "unused_constants_list": self.get_unused_constants(),
            "constants_by_usage": self.get_constants_by_usage(),
            "last_updated": datetime.now().isoformat(),
        }

    def export_usage_data(self, output_file: str = None) -> str:
        """
        导出使用数据

        Args:
            output_file: 输出文件路径

        Returns:
            str: 输出文件路径
        """
        if not output_file:
            output_file = os.path.join(self.project_root, "userdata", "logs", "constants_usage.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 生成报告数据
        report = self.generate_usage_report()
        
        # 导出为JSON
        import json
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        return output_file

    def reset_stats(self) -> None:
        """重置统计信息"""
        self.usage_stats.clear()
        self.change_log.clear()
        self.constants_snapshot.clear()

    def enable_monitoring(self) -> None:
        """启用监控"""
        self.monitoring_enabled = True

    def disable_monitoring(self) -> None:
        """禁用监控"""
        self.monitoring_enabled = False

    def _get_all_constants(self) -> List[str]:
        """获取所有常量列表"""
        all_constants = []
        
        constant_classes = [
            SystemConstants,
            DefaultConfig,
            ErrorMessages,
            SuccessMessages,
            RegexPatterns,
            DangerousPatterns,
            FieldLengths,
            CacheKeys,
            TimeFormats,
            Pagination,
            LogLevel,
            LogType,
            UserRole,
            TaskStatus,
            SyncType,
        ]
        
        for constant_class in constant_classes:
            for attr_name in dir(constant_class):
                if not attr_name.startswith("_"):
                    all_constants.append(attr_name)
        
        return all_constants

    def _log_usage(self, usage_info: Dict[str, Any]) -> None:
        """记录使用日志"""
        # 这里可以添加日志记录逻辑
        # 例如：写入日志文件、发送到监控系统等
        pass

    def _log_change(self, change_info: Dict[str, Any]) -> None:
        """记录变更日志"""
        # 这里可以添加变更日志记录逻辑
        # 例如：写入变更日志文件、发送告警等
        pass

    def create_usage_dashboard_data(self) -> Dict[str, Any]:
        """
        创建使用仪表板数据

        Returns:
            Dict: 仪表板数据
        """
        usage_by_category = self.get_constants_by_usage()
        
        return {
            "summary": {
                "total_constants": len(self._get_all_constants()),
                "used_constants": len(self.usage_stats),
                "unused_constants": len(self.get_unused_constants()),
                "high_usage_count": len(usage_by_category["high_usage"]),
                "medium_usage_count": len(usage_by_category["medium_usage"]),
                "low_usage_count": len(usage_by_category["low_usage"]),
            },
            "usage_distribution": {
                "high_usage": usage_by_category["high_usage"],
                "medium_usage": usage_by_category["medium_usage"],
                "low_usage": usage_by_category["low_usage"],
                "unused": usage_by_category["unused"],
            },
            "top_used_constants": sorted(
                self.usage_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "recent_changes": self.change_log[-10:] if self.change_log else [],
        }


# 全局监控器实例
constants_monitor = ConstantsMonitor()


def track_constant_usage(constant_name: str, file_path: str = None, line_number: int = None) -> None:
    """
    跟踪常量使用的装饰器函数

    Args:
        constant_name: 常量名称
        file_path: 使用文件路径
        line_number: 使用行号
    """
    constants_monitor.track_usage(constant_name, file_path, line_number)


def track_constant_change(constant_name: str, old_value: Any, new_value: Any, file_path: str = None) -> None:
    """
    跟踪常量变更的函数

    Args:
        constant_name: 常量名称
        old_value: 旧值
        new_value: 新值
        file_path: 变更文件路径
    """
    constants_monitor.track_change(constant_name, old_value, new_value, file_path)


def get_constants_usage_report() -> Dict[str, Any]:
    """
    获取常量使用报告

    Returns:
        Dict: 使用报告数据
    """
    return constants_monitor.generate_usage_report()


def get_constants_dashboard_data() -> Dict[str, Any]:
    """
    获取常量仪表板数据

    Returns:
        Dict: 仪表板数据
    """
    return constants_monitor.create_usage_dashboard_data()


def main():
    """主函数"""
    # 创建监控器实例
    monitor = ConstantsMonitor()
    
    # 启用监控
    monitor.enable_monitoring()
    
    # 模拟一些使用情况
    monitor.track_usage("DEFAULT_PAGE_SIZE", "app/routes/dashboard.py", 10)
    monitor.track_usage("MAX_PAGE_SIZE", "app/routes/dashboard.py", 15)
    monitor.track_usage("DEFAULT_PAGE_SIZE", "app/routes/instances.py", 20)
    
    # 生成报告
    report = monitor.generate_usage_report()
    print("常量使用报告:")
    print(f"总常量数: {report['total_constants']}")
    print(f"已使用常量数: {report['used_constants']}")
    print(f"未使用常量数: {report['unused_constants']}")
    print(f"使用率: {report['usage_rate']:.2f}%")
    
    # 导出数据
    output_file = monitor.export_usage_data()
    print(f"使用数据已导出到: {output_file}")


if __name__ == "__main__":
    main()
