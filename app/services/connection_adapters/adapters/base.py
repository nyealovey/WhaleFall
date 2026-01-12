"""数据库连接基类与公共工具."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, TypeAlias

from app.types import DBAPIConnection, JsonValue
from app.utils.database_type_utils import get_database_type_default_schema
from app.utils.structlog_config import get_db_logger

if TYPE_CHECKING:
    from app.models.instance import Instance


def get_default_schema(db_type: str) -> str:
    """根据数据库类型返回默认 schema/database 名称."""
    return get_database_type_default_schema(db_type)


QueryParams: TypeAlias = Sequence[JsonValue] | Mapping[str, JsonValue] | None
QueryResultRow: TypeAlias = Sequence[JsonValue]
QueryResult: TypeAlias = list[QueryResultRow]

__all__ = [
    "ConnectionAdapterError",
    "DBAPIConnection",
    "DatabaseConnection",
    "QueryParams",
    "QueryResult",
    "QueryResultRow",
    "get_default_schema",
]


class ConnectionAdapterError(RuntimeError):
    """数据库连接适配器异常."""


class DatabaseConnection(ABC):
    """数据库连接抽象基类."""

    def __init__(self, instance: Instance) -> None:
        """初始化连接适配器并绑定实例."""
        self.instance = instance
        self.db_logger = get_db_logger()
        self.connection: object | None = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """建立数据库连接."""

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据库连接."""

    @abstractmethod
    def test_connection(self) -> dict[str, JsonValue]:
        """测试数据库连接结果."""

    @abstractmethod
    def execute_query(self, query: str, params: QueryParams = None) -> QueryResult:
        """执行查询并返回结果."""

    @abstractmethod
    def get_version(self) -> str | None:
        """获取数据库版本号."""
