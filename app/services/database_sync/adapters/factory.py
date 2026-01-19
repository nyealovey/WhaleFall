"""容量同步适配器工厂.

根据数据库类型返回对应的容量同步适配器实例.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.constants import DatabaseType
from app.services.database_sync.adapters.mysql_adapter import MySQLCapacityAdapter
from app.services.database_sync.adapters.oracle_adapter import OracleCapacityAdapter
from app.services.database_sync.adapters.postgresql_adapter import PostgreSQLCapacityAdapter
from app.services.database_sync.adapters.sqlserver_adapter import SQLServerCapacityAdapter
from app.utils.database_type_utils import normalize_database_type

if TYPE_CHECKING:
    from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter

_ADAPTERS: dict[str, type[BaseCapacityAdapter]] = {
    DatabaseType.MYSQL: MySQLCapacityAdapter,
    DatabaseType.POSTGRESQL: PostgreSQLCapacityAdapter,
    DatabaseType.SQLSERVER: SQLServerCapacityAdapter,
    DatabaseType.ORACLE: OracleCapacityAdapter,
}


def get_capacity_adapter(db_type: str) -> BaseCapacityAdapter:
    """根据数据库类型获取容量同步适配器实例.

    Args:
        db_type: 数据库类型(mysql、postgresql、sqlserver、oracle).

    Returns:
        对应的容量同步适配器实例.

    Raises:
        ValueError: 当数据库类型不支持时抛出.

    Example:
        >>> adapter = get_capacity_adapter('mysql')
        >>> type(adapter).__name__
        'MySQLCapacityAdapter'

    """
    normalized = normalize_database_type(db_type)
    adapter_cls = _ADAPTERS.get(normalized)
    if not adapter_cls:
        msg = f"不支持的数据库类型: {db_type}"
        raise ValueError(msg)
    return adapter_cls()
