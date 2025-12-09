"""数据库连接工厂,依据实例类型选择适配器."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.utils.structlog_config import log_error

from .adapters import (
    DatabaseConnection,
    MySQLConnection,
    OracleConnection,
    PostgreSQLConnection,
    SQLServerConnection,
)

if TYPE_CHECKING:
    from app.models.instance import Instance


class ConnectionFactory:
    """数据库连接工厂.

    根据实例的数据库类型创建对应的连接适配器.

    Attributes:
        CONNECTION_CLASSES: 数据库类型到连接类的映射字典.

    Example:
        >>> instance = Instance(db_type='mysql', host='localhost')
        >>> connection = ConnectionFactory.create_connection(instance)
        >>> if connection:
        ...     connection.connect()

    """

    CONNECTION_CLASSES = {
        "mysql": MySQLConnection,
        "postgresql": PostgreSQLConnection,
        "sqlserver": SQLServerConnection,
        "oracle": OracleConnection,
    }

    @staticmethod
    def create_connection(instance: Instance) -> DatabaseConnection | None:
        """创建数据库连接对象.

        根据实例的数据库类型选择对应的连接适配器类并实例化.

        Args:
            instance: 数据库实例对象,包含连接所需的配置信息.

        Returns:
            数据库连接对象,如果数据库类型不支持则返回 None.

        Example:
            >>> instance = Instance(db_type='mysql')
            >>> conn = ConnectionFactory.create_connection(instance)
            >>> conn is not None
            True

        """
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
        """测试数据库连接.

        创建连接对象并执行连接测试.

        Args:
            instance: 数据库实例对象.

        Returns:
            测试结果字典,包含 success 和 error/message 字段.
            格式:{'success': bool, 'error': str} 或 {'success': bool, 'message': str}

        Example:
            >>> result = ConnectionFactory.test_connection(instance)
            >>> result['success']
            True

        """
        connection = ConnectionFactory.create_connection(instance)
        if not connection:
            return {"success": False, "error": f"不支持的数据库类型: {instance.db_type}"}
        return connection.test_connection()

    @staticmethod
    def get_supported_types() -> list[str]:
        """获取支持的数据库类型列表.

        Returns:
            支持的数据库类型列表,如 ['mysql', 'postgresql', 'oracle', 'sqlserver'].

        """
        return list(ConnectionFactory.CONNECTION_CLASSES.keys())

    @staticmethod
    def is_type_supported(db_type: str) -> bool:
        """检查数据库类型是否支持.

        Args:
            db_type: 数据库类型字符串.

        Returns:
            如果支持该数据库类型返回 True,否则返回 False.

        Example:
            >>> ConnectionFactory.is_type_supported('mysql')
            True
            >>> ConnectionFactory.is_type_supported('mongodb')
            False

        """
        return db_type.lower() in ConnectionFactory.CONNECTION_CLASSES
