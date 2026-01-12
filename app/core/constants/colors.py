"""颜色常量定义 - 基于Flatly主题的统一色彩系统."""

from typing import ClassVar


class ThemeColors:
    """主题颜色常量."""

    # Flatly主题标准颜色映射
    COLOR_MAP: ClassVar[dict[str, dict[str, str]]] = {
        "primary": {
            "value": "#18bc9c",
            "name": "主色绿",
            "description": "主要操作和重要信息",
            "css_class": "bg-primary",
        },
        "danger": {
            "value": "#e74c3c",
            "name": "危险红",
            "description": "高风险和危险操作",
            "css_class": "bg-danger",
        },
        "warning": {
            "value": "#f39c12",
            "name": "警告橙",
            "description": "需要注意的操作",
            "css_class": "bg-warning",
        },
        "info": {
            "value": "#3498db",
            "name": "信息蓝",
            "description": "普通信息和标准操作",
            "css_class": "bg-info",
        },
        "secondary": {
            "value": "#95a5a6",
            "name": "次要灰",
            "description": "次要信息和禁用状态",
            "css_class": "bg-secondary",
        },
        "success": {
            "value": "#18bc9c",
            "name": "成功绿",
            "description": "成功状态和安全操作",
            "css_class": "bg-success",
        },
        "dark": {
            "value": "#2c3e50",
            "name": "深色",
            "description": "重要信息和标题",
            "css_class": "bg-dark",
        },
        "light": {
            "value": "#ecf0f1",
            "name": "浅色",
            "description": "背景和辅助信息",
            "css_class": "bg-light",
        },
    }
