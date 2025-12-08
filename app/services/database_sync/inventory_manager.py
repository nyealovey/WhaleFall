"""容量同步库存管理器,实现 instance_databases 的增量更新."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.instance_database import InstanceDatabase
from app.services.database_sync.database_filters import database_sync_filter_manager
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.models.instance import Instance


class InventoryManager:
    """负责维护 instance_databases 表的增量同步逻辑."""

    def __init__(self, filter_manager=database_sync_filter_manager) -> None:
        self.logger = get_system_logger()
        self.filter_manager = filter_manager

    def synchronize(
        self,
        instance: Instance,
        metadata: Iterable[dict],
    ) -> dict:
        """根据远端数据库列表同步 instance_databases.

        Args:
            instance: 数据库实例
            metadata: 包含 database_name 等字段的迭代器

        Returns:
            dict: 同步统计

        """
        metadata = list(metadata or [])
        today = time_utils.now_china().date()
        now_ts = time_utils.now()

        existing_records: list[InstanceDatabase] = InstanceDatabase.query.filter_by(
            instance_id=instance.id,
        ).all()
        existing_map = {record.database_name: record for record in existing_records}

        seen_names: set[str] = set()
        created = 0
        refreshed = 0
        reactivated = 0
        deactivated = 0

        excluded_names: list[str] = []

        for item in metadata:
            raw_name = item.get("database_name")
            if raw_name is None:
                continue

            is_system = bool(item.get("is_system"))
            if is_system and (instance.db_type or "").lower() != "mysql":
                # 非 MySQL 保持跳过系统库;MySQL 根据需求纳入同步
                continue

            name = str(raw_name).strip()
            if not name:
                continue

            should_exclude, reason = self.filter_manager.should_exclude_database(instance, name)
            if should_exclude:
                excluded_names.append(name)
                self.logger.info(
                    "inventory_database_filtered",
                    instance=instance.name,
                    database=name,
                    reason=reason,
                )
                continue

            seen_names.add(name)
            record = existing_map.get(name)

            if record:
                record.last_seen_date = today
                record.updated_at = now_ts
                if not record.is_active:
                    record.is_active = True
                    record.deleted_at = None
                    reactivated += 1
                else:
                    refreshed += 1
            else:
                new_record = InstanceDatabase(
                    instance_id=instance.id,
                    database_name=name,
                    first_seen_date=today,
                    last_seen_date=today,
                    is_active=True,
                    created_at=now_ts,
                    updated_at=now_ts,
                )
                db.session.add(new_record)
                created += 1

        for record in existing_records:
            if record.database_name not in seen_names and record.is_active:
                record.is_active = False
                record.deleted_at = now_ts
                record.updated_at = now_ts
                deactivated += 1

        try:
            db.session.commit()
        except SQLAlchemyError as exc:
            db.session.rollback()
            self.logger.error(
                "inventory_sync_commit_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            raise

        summary = {
            "created": created,
            "refreshed": refreshed,
            "reactivated": reactivated,
            "deactivated": deactivated,
            "active_databases": sorted(seen_names),
            "filtered_databases": sorted(excluded_names),
            "synchronized_databases": sorted(seen_names),
        }

        self.logger.info(
            "inventory_sync_completed",
            instance=instance.name,
            **summary,
        )
        return summary
