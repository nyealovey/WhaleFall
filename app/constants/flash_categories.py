"""Flask Flash消息类别常量.

定义Flash消息的标准类别,避免魔法字符串.
"""

from __future__ import annotations

from typing import ClassVar


class FlashCategory:
    """Flask Flash消息类别常量.

    定义标准的Flash消息类别,用于前端显示不同样式的提示消息.
    这些类别对应Bootstrap的alert样式类.
    """

    # 消息类别(对应Bootstrap alert类)
    SUCCESS = "success"     # 成功消息(绿色)
    ERROR = "error"         # 错误消息(红色)
    WARNING = "warning"     # 警告消息(黄色)
    INFO = "info"           # 信息消息(蓝色)
    DANGER = "danger"       # 危险消息(红色,同error)
    PRIMARY = "primary"     # 主要消息(蓝色)
    SECONDARY = "secondary" # 次要消息(灰色)

    ALL: ClassVar[tuple[str, ...]] = (SUCCESS, ERROR, WARNING, INFO, DANGER, PRIMARY, SECONDARY)

    BOOTSTRAP_CLASSES: ClassVar[dict[str, str]] = {
        SUCCESS: "alert-success",
        ERROR: "alert-danger",
        WARNING: "alert-warning",
        INFO: "alert-info",
        DANGER: "alert-danger",
        PRIMARY: "alert-primary",
        SECONDARY: "alert-secondary",
    }

    ICONS: ClassVar[dict[str, str]] = {
        SUCCESS: "check-circle",
        ERROR: "exclamation-circle",
        WARNING: "exclamation-triangle",
        INFO: "info-circle",
        DANGER: "times-circle",
        PRIMARY: "star",
        SECONDARY: "circle",
    }

    # 辅助方法

    @classmethod
    def is_valid(cls, category: str) -> bool:
        """验证消息类别是否有效.

        Args:
            category: 消息类别字符串

        Returns:
            bool: 是否为有效类别

        """
        return category in cls.ALL

    @classmethod
    def get_bootstrap_class(cls, category: str) -> str:
        """获取Bootstrap CSS类名.

        Args:
            category: 消息类别字符串

        Returns:
            str: Bootstrap CSS类名

        """
        return cls.BOOTSTRAP_CLASSES.get(category, "alert-info")

    @classmethod
    def get_icon(cls, category: str) -> str:
        """获取消息类别对应的图标.

        Args:
            category: 消息类别字符串

        Returns:
            str: 图标名称

        """
        return cls.ICONS.get(category, "info-circle")

    @classmethod
    def normalize(cls, category: str) -> str:
        """规范化消息类别.

        处理别名和大小写问题.

        Args:
            category: 消息类别字符串

        Returns:
            str: 规范化后的类别

        """
        normalized = category.lower().strip()

        # 处理常见别名
        aliases = {
            "err": cls.ERROR,
            "fail": cls.ERROR,
            "failed": cls.ERROR,
            "succ": cls.SUCCESS,
            "ok": cls.SUCCESS,
            "warn": cls.WARNING,
            "information": cls.INFO,
        }

        return aliases.get(normalized, normalized)
