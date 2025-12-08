"""账户同步适配器工厂。.

根据数据库类型返回对应的账户同步适配器实例。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.accounts_sync.adapters.mysql_adapter import MySQLAccountAdapter
from app.services.accounts_sync.adapters.oracle_adapter import OracleAccountAdapter
from app.services.accounts_sync.adapters.postgresql_adapter import PostgreSQLAccountAdapter
from app.services.accounts_sync.adapters.sqlserver_adapter import SQLServerAccountAdapter

if TYPE_CHECKING:
    from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter

# 其他数据库适配器在后续实现

_ADAPTERS: dict[str, type[BaseAccountAdapter]] = {
    "mysql": MySQLAccountAdapter,
    "postgresql": PostgreSQLAccountAdapter,
    "sqlserver": SQLServerAccountAdapter,
    "oracle": OracleAccountAdapter,
}


def get_account_adapter(db_type: str) -> BaseAccountAdapter:
    """根据数据库类型获取账户同步适配器实例。.

    Args:
        db_type: 数据库类型（mysql、postgresql、sqlserver、oracle）。

    Returns:
        对应的账户同步适配器实例。

    Raises:
        ValueError: 当数据库类型不支持时抛出。

    Example:
        >>> adapter = get_account_adapter('mysql')
        >>> type(adapter).__name__
        'MySQLAccountAdapter'

    """
    normalized = (db_type or "").lower()
    adapter_cls = _ADAPTERS.get(normalized)
    if not adapter_cls:
        msg = f"不支持的数据库类型: {db_type}"
        raise ValueError(msg)
    return adapter_cls()
