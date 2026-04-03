"""数据库统计读取服务."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, cast

from app.core.constants import SyncStatus
from app.core.types.database_statistics import (
    DatabaseCapacityRanking,
    DatabaseDbTypeStat,
    DatabaseInstanceStat,
    DatabaseStatisticsResult,
    DatabaseSyncStatusStat,
)
from app.repositories.database_statistics_repository import DatabaseStatisticsRepository
from app.services.ledgers.database_ledger_service import (
    RECENT_SYNC_THRESHOLD_HOURS,
    STALE_SYNC_THRESHOLD_HOURS,
    DatabaseLedgerService,
)
from app.utils.time_utils import time_utils


class DatabaseStatisticsReadService:
    """数据库统计读取服务."""

    def __init__(
        self,
        repository: DatabaseStatisticsRepository | None = None,
        ledger_service: DatabaseLedgerService | None = None,
    ) -> None:
        self._repository = repository or DatabaseStatisticsRepository()
        self._ledger_service = ledger_service or DatabaseLedgerService()

    def build_statistics(self) -> DatabaseStatisticsResult:
        """构建数据库统计结果."""
        summary = self._repository.fetch_summary()
        db_type_rows = self._repository.fetch_db_type_stats()
        instance_rows = self._repository.fetch_instance_stats(limit=10)
        sync_rows = self._repository.fetch_latest_sync_rows()
        capacity_rows = self._repository.fetch_capacity_rankings(limit=10)
        capacity_summary_reader = getattr(self._repository, "fetch_capacity_summary", None)
        capacity_summary = (
            capacity_summary_reader()
            if callable(capacity_summary_reader)
            else {
                "total_size_mb": sum(int(getattr(row, "size_mb", 0) or 0) for row in capacity_rows),
                "avg_size_mb": (
                    sum(int(getattr(row, "size_mb", 0) or 0) for row in capacity_rows) / len(capacity_rows)
                    if capacity_rows
                    else 0
                ),
                "max_size_mb": max((int(getattr(row, "size_mb", 0) or 0) for row in capacity_rows), default=0),
            }
        )

        db_type_stats = [
            DatabaseDbTypeStat(
                db_type=cast(str, getattr(row, "db_type", "")),
                count=int(getattr(row, "count", 0)),
            )
            for row in db_type_rows
        ]
        instance_stats = [
            DatabaseInstanceStat(
                instance_id=int(getattr(row, "instance_id", 0)),
                instance_name=cast(str, getattr(row, "instance_name", "")),
                db_type=cast(str, getattr(row, "db_type", "")),
                count=int(getattr(row, "count", 0)),
            )
            for row in instance_rows
        ]
        sync_status_stats = self._build_sync_status_stats(sync_rows)
        capacity_rankings = [
            DatabaseCapacityRanking(
                instance_id=int(getattr(row, "instance_id", 0)),
                instance_name=cast(str, getattr(row, "instance_name", "")),
                db_type=cast(str, getattr(row, "db_type", "")),
                database_name=cast(str, getattr(row, "database_name", "")),
                size_mb=int(getattr(row, "size_mb", 0) or 0),
                size_label=self._ledger_service._format_size(int(getattr(row, "size_mb", 0) or 0)),
                collected_at=(
                    getattr(row, "collected_at", None).isoformat() if getattr(row, "collected_at", None) else None
                ),
            )
            for row in capacity_rows
        ]

        deleted_total = int(summary.get("deleted_databases", 0) or 0)

        return DatabaseStatisticsResult(
            total_databases=int(summary.get("total_databases", 0) or 0),
            active_databases=int(summary.get("active_databases", 0) or 0),
            inactive_databases=int(summary.get("inactive_databases", 0) or 0),
            deleted_databases=deleted_total,
            total_instances=int(summary.get("total_instances", 0) or 0),
            total_size_mb=int(capacity_summary.get("total_size_mb", 0) or 0),
            avg_size_mb=float(capacity_summary.get("avg_size_mb", 0) or 0),
            max_size_mb=int(capacity_summary.get("max_size_mb", 0) or 0),
            db_type_stats=db_type_stats,
            instance_stats=instance_stats,
            sync_status_stats=sync_status_stats,
            capacity_rankings=capacity_rankings,
        )

    @staticmethod
    def empty_statistics() -> DatabaseStatisticsResult:
        """构造空统计结果."""
        return DatabaseStatisticsResult(
            total_databases=0,
            active_databases=0,
            inactive_databases=0,
            deleted_databases=0,
            total_instances=0,
            total_size_mb=0,
            avg_size_mb=0,
            max_size_mb=0,
            db_type_stats=[],
            instance_stats=[],
            sync_status_stats=[],
            capacity_rankings=[],
        )

    def _build_sync_status_stats(self, rows: list[Any]) -> list[DatabaseSyncStatusStat]:
        stats_map: OrderedDict[tuple[str, str, str], int] = OrderedDict()
        for row in rows:
            status = self._resolve_sync_status(getattr(row, "collected_at", None))
            key = (
                cast(str, status["value"]),
                cast(str, status["label"]),
                cast(str, status["variant"]),
            )
            stats_map[key] = stats_map.get(key, 0) + 1

        return [
            DatabaseSyncStatusStat(value=value, label=label, variant=variant, count=count)
            for (value, label, variant), count in stats_map.items()
        ]

    @staticmethod
    def _resolve_sync_status(collected_at: datetime | None) -> dict[str, str]:
        if not collected_at:
            return {"value": SyncStatus.PENDING, "label": "待采集", "variant": "secondary"}

        now = time_utils.now()
        delay_hours = (now - collected_at).total_seconds() / 3600
        if delay_hours <= RECENT_SYNC_THRESHOLD_HOURS:
            return {"value": SyncStatus.COMPLETED, "label": "已更新", "variant": "success"}
        if delay_hours <= STALE_SYNC_THRESHOLD_HOURS:
            return {"value": SyncStatus.RUNNING, "label": "待刷新", "variant": "warning"}
        return {"value": SyncStatus.FAILED, "label": "超时", "variant": "danger"}
