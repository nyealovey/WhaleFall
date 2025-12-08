"""容量采集结果持久化工具。"""

from __future__ import annotations

from typing import List
from collections.abc import Iterable

from sqlalchemy import or_, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import db
from app.models.database_size_stat import DatabaseSizeStat
from app.models.instance import Instance
from app.models.instance_size_stat import InstanceSizeStat
from app.models.instance_database import InstanceDatabase
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils


class CapacityPersistence:
    """负责容量采集相关的数据持久化。"""

    def __init__(self) -> None:
        self.logger = get_system_logger()

    def save_database_stats(self, instance: Instance, data: Iterable[dict]) -> int:
        """
        保存数据库容量数据。

        Args:
            instance: 数据库实例对象。
            data: 容量数据可迭代对象。

        Returns:
            int: 成功保存的记录数

        """
        rows = list(data or [])
        if not rows:
            return 0

        current_utc = time_utils.now()
        records: list[dict] = []

        for item in rows:
            try:
                record = {
                    "instance_id": instance.id,
                    "database_name": item["database_name"],
                    "size_mb": item["size_mb"],
                    "data_size_mb": item.get("data_size_mb"),
                    "log_size_mb": item.get("log_size_mb"),
                    "collected_date": item["collected_date"],
                    "collected_at": item["collected_at"],
                    "created_at": current_utc,
                    "updated_at": current_utc,
                }
            except KeyError as exc:  # 缺少关键字段直接跳过
                self.logger.error(
                    "save_database_stat_invalid_payload",
                    instance=instance.name,
                    payload=item,
                    missing_field=str(exc),
                )
                continue

            records.append(record)

        if not records:
            self.logger.warning(
                "skip_database_stats_upsert_no_valid_rows",
                instance=instance.name,
            )
            return 0

        saved = len(records)

        insert_stmt = pg_insert(DatabaseSizeStat).values(records)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                DatabaseSizeStat.instance_id,
                DatabaseSizeStat.database_name,
                DatabaseSizeStat.collected_date,
            ],
            set_={
                "size_mb": insert_stmt.excluded.size_mb,
                "data_size_mb": insert_stmt.excluded.data_size_mb,
                "log_size_mb": insert_stmt.excluded.log_size_mb,
                "collected_at": insert_stmt.excluded.collected_at,
                "updated_at": current_utc,
            },
        )

        try:
            db.session.execute(upsert_stmt)
        except SQLAlchemyError as exc:
            db.session.rollback()
            self.logger.error(
                "save_database_stats_upsert_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            raise

        try:
            db.session.commit()
            self.logger.info(
                "save_database_stats_success",
                instance=instance.name,
                saved_count=saved,
            )
        except SQLAlchemyError as exc:
            db.session.rollback()
            self.logger.error(
                "save_database_stats_commit_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            raise

        return saved

    def save_instance_stats(self, instance: Instance, data: Iterable[dict]) -> bool:
        """
        保存实例总体容量数据。

        Args:
            instance: 数据库实例对象。
            data: 容量数据可迭代对象。

        Returns:
            bool: 是否成功保存

        """
        rows = list(data or [])
        if not rows:
            self.logger.warning(
                "skip_instance_stats_save_no_data",
                instance=instance.name,
            )
            return False

        total_size = sum(item["size_mb"] for item in rows)
        database_count = len(rows)

        china_now = time_utils.now_china()
        collected_date = china_now.date()
        now_utc = time_utils.now()

        payload = {
            "instance_id": instance.id,
            "total_size_mb": total_size,
            "database_count": database_count,
            "collected_date": collected_date,
            "collected_at": now_utc,
            "is_deleted": False,
            "deleted_at": None,
            "created_at": now_utc,
            "updated_at": now_utc,
        }

        insert_stmt = pg_insert(InstanceSizeStat).values(payload)
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                InstanceSizeStat.instance_id,
                InstanceSizeStat.collected_date,
            ],
            index_where=text("is_deleted = false"),
            set_={
                "total_size_mb": insert_stmt.excluded.total_size_mb,
                "database_count": insert_stmt.excluded.database_count,
                "collected_at": insert_stmt.excluded.collected_at,
                "updated_at": insert_stmt.excluded.updated_at,
                "is_deleted": False,
                "deleted_at": None,
            },
        )

        try:
            db.session.execute(upsert_stmt)
            self.logger.info(
                "save_instance_stats_success",
                instance=instance.name,
                total_size_mb=total_size,
                database_count=database_count,
            )
            return True
        except SQLAlchemyError as exc:
            self.logger.error(
                "save_instance_stats_failed",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return False

    def update_instance_total_size(self, instance: Instance) -> bool:
        """根据当天采集数据刷新实例汇总。

        Args:
            instance: 需要更新的数据库实例。

        Returns:
            bool: 更新成功返回 True，缺少数据或提交失败返回 False。

        """
        today = time_utils.now_china().date()
        stats: list[DatabaseSizeStat] = (
            DatabaseSizeStat.query
            .outerjoin(
                InstanceDatabase,
                (InstanceDatabase.instance_id == DatabaseSizeStat.instance_id)
                & (InstanceDatabase.database_name == DatabaseSizeStat.database_name),
            )
            .filter(
                DatabaseSizeStat.instance_id == instance.id,
                DatabaseSizeStat.collected_date == today,
                or_(
                    InstanceDatabase.is_active.is_(True),
                    InstanceDatabase.is_active.is_(None),
                ),
            )
            .all()
        )

        if not stats:
            self.logger.warning(
                "update_instance_total_size_skipped",
                instance=instance.name,
            )
            return False

        total_size = sum(stat.size_mb for stat in stats)
        database_count = len(stats)

        success = self.save_instance_stats(
            instance,
            [{"size_mb": stat.size_mb} for stat in stats],
        )

        if success:
            try:
                db.session.commit()
            except SQLAlchemyError as exc:
                db.session.rollback()
                self.logger.error(
                    "update_instance_total_size_commit_failed",
                    instance=instance.name,
                    error=str(exc),
                    exc_info=True,
                )
                return False

            self.logger.info(
                "update_instance_total_size_success",
                instance=instance.name,
                total_size_mb=total_size,
                database_count=database_count,
            )
            return True

        return False
