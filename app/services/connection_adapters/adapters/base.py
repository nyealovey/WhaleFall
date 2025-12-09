"""数据库连接基类与公共工具."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from app.services.database_type_service import DatabaseTypeService
from app.utils.structlog_config import get_db_logger

if TYPE_CHECKING:
    from app.models.instance import Instance


def get_default_schema(db_type: str) -> str:
    """根据数据库类型返回默认 schema/database 名称.

    Args:
        db_type: 数据库类型名称(如 'mysql'、'postgresql').

    Returns:
        默认 schema 名称,如果未配置则返回空字符串.

    Example:
        >>> get_default_schema('mysql')
        'mysql'

    """
    config = DatabaseTypeService.get_type_by_name(db_type)
    return config.default_schema if config and config.default_schema else ""


class ConnectionAdapterError(RuntimeError):
    """数据库连接适配器异常."""


class DatabaseConnection(ABC):
    """数据库连接抽象基类.

    定义数据库连接的标准接口,所有数据库类型的连接适配器都应继承此基类.

    Attributes:
        instance: 数据库实例对象.
        db_logger: 数据库日志记录器.
        connection: 底层数据库连接对象.
        is_connected: 连接状态标志.

    Example:
        >>> class MySQLConnection(DatabaseConnection):
        ...     def connect(self):
        ...         # 实现连接逻辑
        ...         pass

    """

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.db_logger = get_db_logger()
        self.connection: Any | None = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """建立数据库连接.

        Returns:
            连接成功返回 True,失败返回 False.

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据库连接.

        Returns:
            None

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """测试数据库连接结果.

        Returns:
            测试结果字典,包含连接状态、版本信息等.

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """

    @abstractmethod
    def execute_query(self, query: str, params: Any | None = None) -> Any:
        """执行查询并返回结果.

        Args:
            query: SQL 查询语句.
            params: 可选的查询参数.

        Returns:
            查询结果,通常为行列表.

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """

    @abstractmethod
    def get_version(self) -> str | None:
        """获取数据库版本号.

        Returns:
            数据库版本字符串,获取失败返回 None.

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """
