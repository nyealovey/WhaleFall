"""表容量采集适配器基类,约束 table sizes 的实现接口."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from app.utils.structlog_config import get_system_logger

if TYPE_CHECKING:
    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection


class BaseTableSizeAdapter:
    """表容量采集适配器基类,定义表级别容量采集接口."""

    def __init__(self) -> None:
        """初始化适配器并准备 logger."""
        self.logger = get_system_logger()

    def fetch_table_sizes(
        self,
        instance: Instance,
        connection: DatabaseConnection,
        database_name: str,
    ) -> list[dict[str, object]]:
        """采集指定 database 下各表容量.

        Args:
            instance: 实例对象(用于日志).
            connection: 数据库连接.
            database_name: 目标 database 名称.

        Returns:
            list[dict[str, object]]: 表容量列表(统一字段结构).

        """
        raise NotImplementedError

    @staticmethod
    def _safe_to_int(value: object) -> int | None:
        if value is None or isinstance(value, bool):
            return None

        result: int | None = None
        if isinstance(value, int):
            result = value
        elif isinstance(value, (float, Decimal)):
            try:
                result = int(value)
            except (TypeError, ValueError):
                result = None
        elif isinstance(value, str):
            try:
                result = int(float(value))
            except ValueError:
                result = None

        return result
