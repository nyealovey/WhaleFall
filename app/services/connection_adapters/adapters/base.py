"""数据库连接基类与公共工具。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.instance import Instance
from app.services.database_type_service import DatabaseTypeService
from app.utils.structlog_config import get_db_logger


def get_default_schema(db_type: str) -> str:
    """根据数据库类型返回默认 schema/database 名称。"""
    config = DatabaseTypeService.get_type_by_name(db_type)
    return config.default_schema if config and config.default_schema else ""


class DatabaseConnection(ABC):
    """数据库连接抽象基类。"""

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.db_logger = get_db_logger()
        self.connection: Any | None = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        """建立数据库连接。"""

    @abstractmethod
    def disconnect(self) -> None:
        """断开数据库连接。"""

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """测试数据库连接结果。"""

    @abstractmethod
    def execute_query(self, query: str, params: Any | None = None) -> Any:  # noqa: ANN401
        """执行查询并返回结果。"""

    @abstractmethod
    def get_version(self) -> str | None:
        """获取数据库版本号。"""
