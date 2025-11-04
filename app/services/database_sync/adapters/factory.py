from __future__ import annotations

from typing import Dict, Type

from app.services.database_sync.adapters.base_adapter import BaseCapacityAdapter
from app.services.database_sync.adapters.mysql_adapter import MySQLCapacityAdapter
from app.services.database_sync.adapters.oracle_adapter import OracleCapacityAdapter
from app.services.database_sync.adapters.postgresql_adapter import PostgreSQLCapacityAdapter
from app.services.database_sync.adapters.sqlserver_adapter import SQLServerCapacityAdapter


_ADAPTERS: Dict[str, Type[BaseCapacityAdapter]] = {
    "mysql": MySQLCapacityAdapter,
    "postgresql": PostgreSQLCapacityAdapter,
    "sqlserver": SQLServerCapacityAdapter,
    "oracle": OracleCapacityAdapter,
}


def get_capacity_adapter(db_type: str) -> BaseCapacityAdapter:
    """根据数据库类型返回对应适配器实例。"""
    normalized = (db_type or "").lower()
    adapter_cls = _ADAPTERS.get(normalized)
    if not adapter_cls:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    return adapter_cls()
