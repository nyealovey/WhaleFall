"""数据库类型工具.

从 `app/core/constants/database_types.py` 读取静态映射,提供规范化/展示等纯函数.
"""

from __future__ import annotations

from typing import Final

from app.core.constants.database_types import DatabaseType

_DATABASE_TYPE_ALIASES: Final[dict[str, str]] = {
    "mssql": DatabaseType.SQLSERVER,
    "sql server": DatabaseType.SQLSERVER,
    "postgres": DatabaseType.POSTGRESQL,
    "pg": DatabaseType.POSTGRESQL,
}


def normalize_database_type(db_type: str) -> str:
    """规范化数据库类型字符串(转小写+trim,并处理常见别名)."""
    normalized = db_type.lower().strip()
    return _DATABASE_TYPE_ALIASES.get(normalized, normalized)


def get_database_type_display_name(db_type: str) -> str:
    normalized = normalize_database_type(db_type)
    return DatabaseType.DISPLAY_NAMES.get(normalized, db_type)


def get_database_type_icon(db_type: str) -> str:
    normalized = normalize_database_type(db_type)
    return DatabaseType.ICONS.get(normalized, "fa-database")


def get_database_type_color(db_type: str) -> str:
    normalized = normalize_database_type(db_type)
    return DatabaseType.COLORS.get(normalized, "primary")


def get_database_type_default_port(db_type: str) -> int | None:
    normalized = normalize_database_type(db_type)
    return DatabaseType.DEFAULT_PORTS.get(normalized)


def get_database_type_default_schema(db_type: str) -> str:
    normalized = normalize_database_type(db_type)
    return DatabaseType.DEFAULT_SCHEMAS.get(normalized, "")


def database_type_requires_port(db_type: str) -> bool:
    return get_database_type_default_port(db_type) is not None


def build_database_type_select_option(db_type: str) -> dict[str, str]:
    """构造统一的下拉选项字典.

    Shape: {"value": str, "label": str, "icon": str, "color": str}
    """
    return {
        "value": db_type,
        "label": get_database_type_display_name(db_type),
        "icon": get_database_type_icon(db_type),
        "color": get_database_type_color(db_type),
    }
