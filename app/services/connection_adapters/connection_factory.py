#!/usr/bin/env python3

"""数据库连接工厂，依据实例类型选择适配器。"""

from __future__ import annotations

from typing import Any

from app.models.instance import Instance
from app.utils.structlog_config import log_error

from .adapters import (
    DatabaseConnection,
    MySQLConnection,
    OracleConnection,
    PostgreSQLConnection,
    SQLServerConnection,
)


class ConnectionFactory:
    """数据库连接工厂。"""

    CONNECTION_CLASSES = {
        "mysql": MySQLConnection,
        "postgresql": PostgreSQLConnection,
        "sqlserver": SQLServerConnection,
        "oracle": OracleConnection,
    }

    @staticmethod
    def create_connection(instance: Instance) -> DatabaseConnection | None:
        db_type = (instance.db_type or "").lower()
        connection_class = ConnectionFactory.CONNECTION_CLASSES.get(db_type)
        if not connection_class:
            log_error(
                "不支持的数据库类型",
                module="connection",
                instance_id=instance.id,
                db_type=db_type,
            )
            return None
        return connection_class(instance)

    @staticmethod
    def test_connection(instance: Instance) -> dict[str, Any]:
        connection = ConnectionFactory.create_connection(instance)
        if not connection:
            return {"success": False, "error": f"不支持的数据库类型: {instance.db_type}"}
        return connection.test_connection()

    @staticmethod
    def get_supported_types() -> list[str]:
        return list(ConnectionFactory.CONNECTION_CLASSES.keys())

    @staticmethod
    def is_type_supported(db_type: str) -> bool:
        return db_type.lower() in ConnectionFactory.CONNECTION_CLASSES
