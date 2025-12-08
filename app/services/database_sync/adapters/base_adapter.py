"""容量采集适配器基类,约束 inventory 与 capacity 的实现接口.."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.utils.structlog_config import get_system_logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from app.models.instance import Instance


class BaseCapacityAdapter:
    """容量同步适配器基类,定义库存与容量采集接口..

    所有数据库类型的容量适配器都应继承此基类并实现其抽象方法.

    Attributes:
        logger: 系统日志记录器.

    Example:
        >>> class MySQLAdapter(BaseCapacityAdapter):
        ...     def fetch_inventory(self, instance, connection):
        ...         return [{'database_name': 'mydb', 'is_system': False}]

    """

    def __init__(self) -> None:
        self.logger = get_system_logger()

    def fetch_inventory(self, instance: Instance, connection) -> list[dict]:
        """列出实例当前的数据库/表空间..

        Args:
            instance: 实例对象.
            connection: 数据库连接对象.

        Returns:
            数据库清单列表,每个元素包含:
            - database_name: 数据库名称
            - is_system: 是否为系统数据库

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """
        raise NotImplementedError

    def fetch_capacity(
        self,
        instance: Instance,
        connection,
        target_databases: Sequence[str] | None = None,
    ) -> list[dict]:
        """采集指定数据库的容量数据..

        Args:
            instance: 实例对象.
            connection: 数据库连接对象.
            target_databases: 目标数据库列表,可选.如果为 None 则采集所有数据库.

        Returns:
            容量数据列表,每个元素包含:
            - database_name: 数据库名称
            - size_mb: 总大小(MB)
            - data_size_mb: 数据大小(MB)
            - log_size_mb: 日志大小(MB)
            - collected_date: 采集日期
            - collected_at: 采集时间
            - is_system: 是否为系统数据库

        Raises:
            NotImplementedError: 子类必须实现此方法.

        """
        raise NotImplementedError

    @staticmethod
    def _normalize_targets(target_databases: Iterable[str] | None) -> set[str] | None:
        """规范化目标数据库列表..

        Args:
            target_databases: 目标数据库列表,可选.

        Returns:
            规范化后的数据库名称集合,如果输入为 None 则返回 None.
            空列表会被转换为空集合.

        """
        if target_databases is None:
            return None
        normalized = {str(name).strip() for name in target_databases if str(name).strip()}
        return normalized or set()
