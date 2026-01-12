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
    SUCCESS = "success"  # 成功消息(绿色)
    ERROR = "error"  # 错误消息(红色)
    WARNING = "warning"  # 警告消息(黄色)
    INFO = "info"  # 信息消息(蓝色)
    DANGER = "danger"  # 危险消息(红色,同error)
    PRIMARY = "primary"  # 主要消息(蓝色)
    SECONDARY = "secondary"  # 次要消息(灰色)

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
