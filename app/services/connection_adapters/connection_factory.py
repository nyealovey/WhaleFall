"""数据库连接工厂,依据实例类型选择适配器."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from app.core.constants import DatabaseType
from app.utils.database_type_utils import normalize_database_type
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

    CONNECTION_CLASSES: ClassVar[dict[str, type[DatabaseConnection]]] = {
        DatabaseType.MYSQL: MySQLConnection,
        DatabaseType.POSTGRESQL: PostgreSQLConnection,
        DatabaseType.SQLSERVER: SQLServerConnection,
        DatabaseType.ORACLE: OracleConnection,
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
        db_type = normalize_database_type(instance.db_type)
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
            测试结果字典,包含 success 与 message 字段(必填),失败时可选包含 error 字段(诊断信息).
            格式:
            - 成功: {'success': True, 'message': str, ...}
            - 失败: {'success': False, 'message': str, 'error': str, ...}

        Example:
            >>> result = ConnectionFactory.test_connection(instance)
            >>> result['success']
            True

        """
        connection = ConnectionFactory.create_connection(instance)
        if not connection:
            return {
                "success": False,
                "message": "不支持的数据库类型",
                "error": f"不支持的数据库类型: {instance.db_type}",
            }
        return connection.test_connection()
