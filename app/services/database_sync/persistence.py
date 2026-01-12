"""容量采集结果持久化工具."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app.repositories.capacity_persistence_repository import CapacityPersistenceRepository
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Iterable

    from app.models.instance import Instance


class CapacityPersistence:
    """负责容量采集相关的数据持久化."""

    def __init__(self, repository: CapacityPersistenceRepository | None = None) -> None:
        """初始化容量持久化组件,注入系统日志记录器."""
        self.logger = get_system_logger()
        self._repository = repository or CapacityPersistenceRepository()

    def save_database_stats(self, instance: Instance, data: Iterable[dict]) -> int:
        """保存数据库容量数据.

        Args:
            instance: 数据库实例对象.
            data: 容量数据可迭代对象.

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
                self.logger.exception(
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

        try:
            self._repository.upsert_database_size_stats(records, current_utc=current_utc)
        except SQLAlchemyError as exc:
            self.logger.exception(
                "save_database_stats_upsert_failed",
                instance=instance.name,
                error=str(exc),
            )
            raise
        else:
            self.logger.info(
                "save_database_stats_success",
                instance=instance.name,
                saved_count=saved,
            )

        return saved

    def save_instance_stats(self, instance: Instance, data: Iterable[dict]) -> bool:
        """保存实例总体容量数据.

        Args:
            instance: 数据库实例对象.
            data: 容量数据可迭代对象.

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

        try:
            self._repository.upsert_instance_size_stat(payload, current_utc=now_utc)
        except SQLAlchemyError as exc:
            self.logger.exception(
                "save_instance_stats_failed",
                instance=instance.name,
                error=str(exc),
            )
            return False
        else:
            self.logger.info(
                "save_instance_stats_success",
                instance=instance.name,
                total_size_mb=total_size,
                database_count=database_count,
            )
            return True

    def update_instance_total_size(self, instance: Instance) -> bool:
        """根据当天采集数据刷新实例汇总.

        Args:
            instance: 需要更新的数据库实例.

        Returns:
            bool: 更新成功返回 True,缺少数据或提交失败返回 False.

        """
        today = time_utils.now_china().date()
        stats = self._repository.list_database_size_stats_for_instance_date(
            instance_id=instance.id,
            collected_date=today,
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
            self.logger.info(
                "update_instance_total_size_success",
                instance=instance.name,
                total_size_mb=total_size,
                database_count=database_count,
            )
            return True

        return False
