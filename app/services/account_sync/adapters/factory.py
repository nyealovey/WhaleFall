from __future__ import annotations

from typing import Dict, Type

from app.services.account_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.account_sync.adapters.mysql_adapter import MySQLAccountAdapter
from app.services.account_sync.adapters.postgresql_adapter import PostgreSQLAccountAdapter
from app.services.account_sync.adapters.sqlserver_adapter import SQLServerAccountAdapter
from app.services.account_sync.adapters.oracle_adapter import OracleAccountAdapter

# 其他数据库适配器在后续实现

_ADAPTERS: Dict[str, Type[BaseAccountAdapter]] = {
    "mysql": MySQLAccountAdapter,
    "postgresql": PostgreSQLAccountAdapter,
    "sqlserver": SQLServerAccountAdapter,
    "oracle": OracleAccountAdapter,
}


def get_account_adapter(db_type: str) -> BaseAccountAdapter:
    normalized = (db_type or "").lower()
    adapter_cls = _ADAPTERS.get(normalized)
    if not adapter_cls:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    return adapter_cls()
