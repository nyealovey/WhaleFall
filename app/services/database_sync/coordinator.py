"""容量同步协调器,实现连接、库存同步与容量采集整体流程."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING

from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.services.database_sync.adapters import get_capacity_adapter
from app.services.database_sync.database_filters import database_sync_filter_manager
from app.services.database_sync.inventory_manager import InventoryManager
from app.services.database_sync.persistence import CapacityPersistence
from app.utils.structlog_config import get_system_logger

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from app.models.instance import Instance
    from app.services.connection_adapters.adapters.base import DatabaseConnection


CONNECTION_EXCEPTIONS: tuple[type[Exception], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    LookupError,
    ValueError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class CapacitySyncCoordinator:
    """容量同步协调器,负责组织库存同步与容量采集流程.

    协调数据库容量同步的完整流程,包括:
    - 建立数据库连接
    - 同步数据库清单
    - 采集容量数据
    - 持久化数据

    Attributes:
        instance: 数据库实例对象.
        logger: 系统日志记录器.

    """

    def __init__(self, instance: Instance) -> None:
        """初始化容量同步协调器.

        Args:
            instance: 数据库实例对象.

        """
        self.instance = instance
        self.logger = get_system_logger()
        self._adapter = get_capacity_adapter(instance.db_type)
        self._inventory_manager = InventoryManager(filter_manager=database_sync_filter_manager)
        self._persistence = CapacityPersistence()
        self._connection: DatabaseConnection | None = None

    def __enter__(self) -> CapacitySyncCoordinator:
        """进入上下文管理器并建立连接."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """退出上下文管理器并断开连接."""
        del exc_type, exc_val, exc_tb
        self.disconnect()

    def connect(self) -> bool:
        """建立数据库连接.

        如果连接已存在且有效,则复用现有连接.

        Returns:
            连接成功返回 True,失败返回 False.

        """
        if self._connection and getattr(self._connection, "is_connected", False):
            self.logger.info(
                "capacity_sync_use_existing_connection",
                instance=self.instance.name,
            )
            return True

        connection = ConnectionFactory.create_connection(self.instance)
        if not connection:
            self.logger.error(
                "capacity_sync_connection_factory_failed",
                instance=self.instance.name,
                db_type=self.instance.db_type,
            )
            return False

        try:
            if connection.connect():
                self._connection = connection
                self.logger.info(
                    "capacity_sync_connection_success",
                    instance=self.instance.name,
                    db_type=self.instance.db_type,
                )
                return True
        except CONNECTION_EXCEPTIONS as exc:
            self.logger.exception(
                "capacity_sync_connection_error",
                instance=self.instance.name,
                error=str(exc),
            )

        self.logger.error(
            "capacity_sync_connection_failed",
            instance=self.instance.name,
        )
        return False

    def disconnect(self) -> None:
        """断开数据库连接.

        安全地关闭数据库连接,即使发生异常也会清理连接对象.

        Returns:
            None: 连接关闭或已清理时返回.

        """
        if self._connection:
            try:
                self._connection.disconnect()
            except CONNECTION_EXCEPTIONS as exc:
                self.logger.warning(
                    "capacity_sync_disconnect_error",
                    instance=self.instance.name,
                    error=str(exc),
                    exc_info=True,
                )
            finally:
                self._connection = None

    def synchronize_inventory(self) -> dict:
        """执行库存同步:远端拉取 → instance_databases 落库.

        从远程数据库获取数据库清单,并同步到本地 instance_databases 表.

        Returns:
            同步统计信息字典,包含活跃数据库列表等信息.

        """
        metadata = self.fetch_inventory()
        return self.sync_instance_databases(metadata)

    def fetch_inventory(self) -> list[dict]:
        """获取远程数据库清单.

        Returns:
            数据库元数据列表.

        """
        self._ensure_connection()
        connection = self._connection
        if connection is None:
            msg = "数据库连接未建立"
            raise RuntimeError(msg)
        return self._adapter.fetch_inventory(self.instance, connection)

    def sync_instance_databases(self, metadata: Iterable[dict]) -> dict:
        """同步数据库清单到本地.

        Args:
            metadata: 数据库元数据列表.

        Returns:
            同步统计信息字典.

        """
        return self._inventory_manager.synchronize(self.instance, metadata)

    def collect_capacity(
        self,
        target_databases: Sequence[str] | None = None,
    ) -> list[dict]:
        """采集容量数据.

        从远程数据库采集容量统计数据,支持按数据库名称过滤.

        Args:
            target_databases: 目标数据库名称列表,为 None 时采集所有数据库.

        Returns:
            容量数据列表,每项包含数据库名称、大小等信息.

        """
        self._ensure_connection()

        connection = self._connection
        if connection is None:
            msg = "数据库连接未建立"
            raise RuntimeError(msg)

        filtered_targets = None
        if target_databases is not None:
            allowed, excluded = database_sync_filter_manager.filter_database_names(
                self.instance,
                target_databases,
            )
            if excluded:
                self.logger.info(
                    "capacity_skip_filtered_targets",
                    instance=self.instance.name,
                    filtered=excluded,
                )
            filtered_targets = allowed
            if not filtered_targets:
                return []

        data = self._adapter.fetch_capacity(
            self.instance,
            connection,
            filtered_targets,
        )

        filtered_data, excluded = database_sync_filter_manager.filter_capacity_payload(
            self.instance,
            data,
        )

        if excluded:
            self.logger.info(
                "capacity_skip_filtered_results",
                instance=self.instance.name,
                filtered=excluded,
            )

        return filtered_data

    def save_database_stats(self, data: Iterable[dict]) -> int:
        """保存数据库容量统计数据.

        Args:
            data: 容量数据列表.

        Returns:
            保存的记录数.

        """
        return self._persistence.save_database_stats(self.instance, data)

    def save_instance_stats(self, data: Iterable[dict]) -> bool:
        """保存实例容量统计数据.

        Args:
            data: 容量数据列表.

        Returns:
            保存成功返回 True,失败返回 False.

        """
        return self._persistence.save_instance_stats(self.instance, data)

    def update_instance_total_size(self) -> bool:
        """更新实例总容量.

        Returns:
            更新成功返回 True,失败返回 False.

        """
        return self._persistence.update_instance_total_size(self.instance)

    def collect_and_save(self) -> int:
        """执行完整的库存同步 + 容量采集 + 数据持久化流程.

        按顺序执行:
        1. 同步数据库清单
        2. 采集活跃数据库的容量数据
        3. 保存数据库和实例统计数据
        4. 提交事务

        Returns:
            保存的记录数.

        Raises:
            Exception: 当数据库提交失败时抛出.

        """
        inventory_summary = self.synchronize_inventory()
        active_databases = set(inventory_summary.get("active_databases", []))

        if not active_databases:
            self.logger.info(
                "capacity_sync_skip_no_active_databases",
                instance=self.instance.name,
            )
            return 0

        data = self.collect_capacity(list(active_databases))
        saved_count = self.save_database_stats(data)
        if data:
            self.save_instance_stats(data)
            self.logger.info(
                "capacity_sync_collect_and_save_completed",
                instance=self.instance.name,
                saved_count=saved_count,
            )

        return saved_count

    def _ensure_connection(self) -> None:
        """确保数据库连接已建立.

        如果连接不存在或已断开,则尝试重新连接.

        Returns:
            None: 连接有效或成功重连后返回.

        Raises:
            RuntimeError: 当连接建立失败时抛出.

        """
        if (not self._connection or not getattr(self._connection, "is_connected", False)) and not self.connect():
            msg = "数据库连接未建立"
            raise RuntimeError(msg)
