"""容量同步库存管理器,实现 instance_databases 的增量更新."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.instance_database import InstanceDatabase
from app.services.database_sync.database_filters import (
    DatabaseSyncFilterManager,
    database_sync_filter_manager,
)
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.models.instance import Instance


@dataclass(slots=True)
class InventorySyncStats:
    created: int = 0
    refreshed: int = 0
    reactivated: int = 0
    deactivated: int = 0

    def to_summary(self, *, seen_names: set[str], excluded_names: list[str]) -> dict[str, object]:
        """构建对外的同步统计结果."""
        active_names = sorted(seen_names)
        filtered_names = sorted(excluded_names)
        return {
            "created": self.created,
            "refreshed": self.refreshed,
            "reactivated": self.reactivated,
            "deactivated": self.deactivated,
            "active_databases": active_names,
            "filtered_databases": filtered_names,
            "synchronized_databases": active_names,
        }


class InventoryManager:
    """负责维护 instance_databases 表的增量同步逻辑."""

    def __init__(
        self,
        filter_manager: DatabaseSyncFilterManager = database_sync_filter_manager,
    ) -> None:
        """初始化库存管理器,注入过滤器与日志记录器."""
        self.logger = get_system_logger()
        self.filter_manager = filter_manager

    def synchronize(
        self,
        instance: Instance,
        metadata: Iterable[dict],
    ) -> dict[str, object]:
        """根据远端数据库列表同步 instance_databases.

        Args:
            instance: 数据库实例
            metadata: 包含 database_name 等字段的迭代器

        Returns:
            dict: 同步统计

        """
        metadata_list = list(metadata or [])
        today = time_utils.now_china().date()
        now_ts = time_utils.now()

        existing_records: list[InstanceDatabase] = InstanceDatabase.query.filter_by(
            instance_id=instance.id,
        ).all()
        existing_map = {record.database_name: record for record in existing_records}

        seen_names: set[str] = set()
        excluded_names: list[str] = []
        stats = InventorySyncStats()

        try:
            with db.session.begin_nested():
                for item in metadata_list:
                    name = self._normalize_database_name(item)
                    if name is None:
                        continue

                    if self._should_skip_system_database(instance, item):
                        continue

                    if self._is_filtered_database(instance, name, excluded_names):
                        continue

                    seen_names.add(name)
                    record = existing_map.get(name)

                    if record:
                        self._refresh_existing_record(record, today=today, now_ts=now_ts, stats=stats)
                    else:
                        self._create_new_record(
                            instance_id=instance.id,
                            database_name=name,
                            today=today,
                            now_ts=now_ts,
                        )
                        stats.created += 1

                stats.deactivated = self._deactivate_missing_records(existing_records, seen_names, now_ts)

                db.session.flush()
        except SQLAlchemyError as exc:
            self.logger.exception(
                "inventory_sync_flush_failed",
                instance=instance.name,
                error=str(exc),
            )
            raise
        return self._log_and_return_summary(
            instance,
            stats.to_summary(seen_names=seen_names, excluded_names=excluded_names),
        )

    @staticmethod
    def _normalize_database_name(item: dict) -> str | None:
        raw_name = item.get("database_name")
        if raw_name is None:
            return None
        name = str(raw_name).strip()
        return name or None

    @staticmethod
    def _should_skip_system_database(instance: Instance, item: dict) -> bool:
        is_system = bool(item.get("is_system"))
        if not is_system:
            return False
        # 非 MySQL 保持跳过系统库;MySQL 根据需求纳入同步
        return (instance.db_type or "").lower() != "mysql"

    def _is_filtered_database(self, instance: Instance, name: str, excluded_names: list[str]) -> bool:
        should_exclude, reason = self.filter_manager.should_exclude_database(instance, name)
        if not should_exclude:
            return False
        excluded_names.append(name)
        self.logger.info(
            "inventory_database_filtered",
            instance=instance.name,
            database=name,
            reason=reason,
        )
        return True

    @staticmethod
    def _refresh_existing_record(
        record: InstanceDatabase,
        *,
        today: date,
        now_ts: datetime,
        stats: InventorySyncStats,
    ) -> None:
        record.last_seen_date = today
        record.updated_at = now_ts
        if not record.is_active:
            record.is_active = True
            record.deleted_at = None
            stats.reactivated += 1
        else:
            stats.refreshed += 1

    @staticmethod
    def _create_new_record(
        *,
        instance_id: int,
        database_name: str,
        today: date,
        now_ts: datetime,
    ) -> None:
        new_record = InstanceDatabase()
        new_record.instance_id = instance_id
        new_record.database_name = database_name
        new_record.first_seen_date = today
        new_record.last_seen_date = today
        new_record.is_active = True
        new_record.created_at = now_ts
        new_record.updated_at = now_ts
        db.session.add(new_record)

    @staticmethod
    def _deactivate_missing_records(
        existing_records: list[InstanceDatabase],
        seen_names: set[str],
        now_ts: datetime,
    ) -> int:
        deactivated = 0
        for record in existing_records:
            if record.database_name not in seen_names and record.is_active:
                record.is_active = False
                record.deleted_at = now_ts
                record.updated_at = now_ts
                deactivated += 1
        return deactivated

    def _log_and_return_summary(self, instance: Instance, summary: dict[str, object]) -> dict[str, object]:
        """汇总同步结果并输出日志."""
        self.logger.info("inventory_sync_completed", instance=instance.name, **summary)
        return summary
