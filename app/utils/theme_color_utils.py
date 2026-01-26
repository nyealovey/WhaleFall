"""主题颜色工具.

从 `app/core/constants/colors.py` 读取静态映射,提供颜色校验/展示等纯函数.
"""

from __future__ import annotations

from typing import Final

from app.core.constants.colors import ThemeColors

_DEFAULT_COLOR_KEY: Final[str] = "info"


def is_valid_theme_color(color_key: str) -> bool:
    """判断颜色 key 是否有效."""
    return color_key in ThemeColors.COLOR_MAP


def get_theme_color_info(color_key: str) -> dict[str, str]:
    """获取颜色的完整信息(无效 key 则回退到默认颜色)."""
    info = ThemeColors.COLOR_MAP.get(color_key) or ThemeColors.COLOR_MAP[_DEFAULT_COLOR_KEY]
    return dict(info)


def get_theme_color_value(color_key: str) -> str:
    """获取颜色值(HEX/RGB 等)."""
    return get_theme_color_info(color_key).get("value", ThemeColors.COLOR_MAP[_DEFAULT_COLOR_KEY]["value"])


def get_theme_color_name(color_key: str) -> str:
    """获取颜色名称."""
    return get_theme_color_info(color_key).get("name", ThemeColors.COLOR_MAP[_DEFAULT_COLOR_KEY]["name"])


def get_theme_color_css_class(color_key: str) -> str:
    """获取颜色对应的 CSS class."""
    return get_theme_color_info(color_key).get("css_class", ThemeColors.COLOR_MAP[_DEFAULT_COLOR_KEY]["css_class"])
