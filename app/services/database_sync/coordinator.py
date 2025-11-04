from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from app import db
from app.models.instance import Instance
from app.services.database_sync.adapters import get_capacity_adapter
from app.services.database_sync.inventory_manager import InventoryManager
from app.services.database_sync.persistence import CapacityPersistence
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.utils.structlog_config import get_system_logger


class CapacitySyncCoordinator:
    """容量同步协调器，负责组织库存同步与容量采集流程。"""

    def __init__(self, instance: Instance) -> None:
        self.instance = instance
        self.logger = get_system_logger()
        self._adapter = get_capacity_adapter(instance.db_type)
        self._inventory_manager = InventoryManager()
        self._persistence = CapacityPersistence()
        self._connection = None

    @property
    def inventory_manager(self) -> InventoryManager:
        return self._inventory_manager

    @property
    def persistence(self) -> CapacityPersistence:
        return self._persistence

    def connect(self) -> bool:
        """建立数据库连接。"""
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
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "capacity_sync_connection_error",
                instance=self.instance.name,
                error=str(exc),
                exc_info=True,
            )

        self.logger.error(
            "capacity_sync_connection_failed",
            instance=self.instance.name,
        )
        return False

    def disconnect(self) -> None:
        if self._connection:
            try:
                self._connection.disconnect()
            except Exception as exc:  # noqa: BLE001
                self.logger.warning(
                    "capacity_sync_disconnect_error",
                    instance=self.instance.name,
                    error=str(exc),
                    exc_info=True,
                )
            finally:
                self._connection = None

    def synchronize_inventory(self) -> dict:
        """执行库存同步：远端拉取 → instance_databases 落库。"""
        metadata = self.fetch_inventory()
        return self.sync_instance_databases(metadata)

    def fetch_inventory(self) -> List[dict]:
        self._ensure_connection()
        return self._adapter.fetch_inventory(self.instance, self._connection)

    def sync_instance_databases(self, metadata: Iterable[dict]) -> dict:
        return self._inventory_manager.synchronize(self.instance, metadata)

    def collect_capacity(
        self,
        target_databases: Optional[Sequence[str]] = None,
    ) -> List[dict]:
        """采集容量数据。"""
        self._ensure_connection()
        data = self._adapter.fetch_capacity(self.instance, self._connection, target_databases)
        return data

    def save_database_stats(self, data: Iterable[dict]) -> int:
        return self._persistence.save_database_stats(self.instance, data)

    def save_instance_stats(self, data: Iterable[dict]) -> bool:
        return self._persistence.save_instance_stats(self.instance, data)

    def update_instance_total_size(self) -> bool:
        return self._persistence.update_instance_total_size(self.instance)

    def collect_and_save(self) -> int:
        """执行完整的库存同步 + 容量采集 + 数据持久化流程。"""
        inventory_summary = self.synchronize_inventory()
        active_databases = set(inventory_summary.get("active_databases", []))

        if not active_databases:
            self.logger.info(
                "capacity_sync_skip_no_active_databases",
                instance=self.instance.name,
            )
            return 0

        data = self.collect_capacity(active_databases)
        saved_count = self.save_database_stats(data)
        if data:
            self.save_instance_stats(data)
            try:
                db.session.commit()
            except Exception as exc:  # noqa: BLE001
                db.session.rollback()
                self.logger.error(
                    "capacity_sync_commit_failed",
                    instance=self.instance.name,
                    error=str(exc),
                    exc_info=True,
                )
                raise

            self.logger.info(
                "capacity_sync_collect_and_save_completed",
                instance=self.instance.name,
                saved_count=saved_count,
            )

        return saved_count

    def _ensure_connection(self) -> None:
        if not self._connection or not getattr(self._connection, "is_connected", False):
            if not self.connect():
                raise RuntimeError("数据库连接未建立")
