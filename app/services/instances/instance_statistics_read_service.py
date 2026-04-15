"""实例统计 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import cast

from app.core.types.instance_statistics import (
    InstanceDbTypeStat,
    InstancePortStat,
    InstanceStatisticsResult,
    InstanceVersionStat,
)
from app.repositories.instance_statistics_repository import InstanceStatisticsRepository

BACKUP_STATUS_ORDER = ("backed_up", "backup_stale", "not_backed_up")
BACKUP_STATUS_COUNT_KEYS = {
    "backed_up": "backed_up_instances",
    "backup_stale": "backup_stale_instances",
    "not_backed_up": "not_backed_up_instances",
}


def _build_backup_status_stats(totals: dict[str, int]) -> list[dict[str, object]]:
    return [
        {
            "backup_status": status,
            "count": int(totals.get(BACKUP_STATUS_COUNT_KEYS[status], 0)),
        }
        for status in BACKUP_STATUS_ORDER
    ]


class InstanceStatisticsReadService:
    """实例统计读取服务."""

    def __init__(self, repository: InstanceStatisticsRepository | None = None) -> None:
        """初始化服务并注入仓库."""
        self._repository = repository or InstanceStatisticsRepository()

    def build_statistics(self) -> InstanceStatisticsResult:
        """构建实例统计结果."""
        totals = self._repository.fetch_summary()
        db_type_rows = self._repository.fetch_db_type_stats()
        port_rows = self._repository.fetch_port_stats()
        version_rows = self._repository.fetch_version_stats()

        db_type_stats = [
            InstanceDbTypeStat(
                db_type=cast(str, getattr(row, "db_type", "")),
                count=int(getattr(row, "count", 0)),
            )
            for row in db_type_rows
        ]
        port_stats = [
            InstancePortStat(
                port=cast("int | None", getattr(row, "port", None)),
                count=int(getattr(row, "count", 0)),
            )
            for row in port_rows
        ]
        version_stats = [
            InstanceVersionStat(
                db_type=cast(str, getattr(row, "db_type", "")),
                version=cast(str, getattr(row, "main_version", None) or "未知版本"),
                count=int(getattr(row, "count", 0)),
            )
            for row in version_rows
        ]

        return InstanceStatisticsResult(
            total_instances=totals["total_instances"],
            current_instances=totals["current_instances"],
            active_instances=totals["active_instances"],
            normal_instances=totals["normal_instances"],
            disabled_instances=totals["disabled_instances"],
            deleted_instances=totals["deleted_instances"],
            inactive_instances=totals["disabled_instances"],
            audit_enabled_instances=totals["audit_enabled_instances"],
            high_availability_instances=totals["high_availability_instances"],
            managed_instances=totals["managed_instances"],
            unmanaged_instances=totals["unmanaged_instances"],
            backed_up_instances=totals["backed_up_instances"],
            backup_stale_instances=totals["backup_stale_instances"],
            not_backed_up_instances=totals["not_backed_up_instances"],
            backup_status_stats=_build_backup_status_stats(totals),
            db_types_count=len(db_type_rows),
            db_type_stats=db_type_stats,
            port_stats=port_stats,
            version_stats=version_stats,
        )

    @staticmethod
    def empty_statistics() -> InstanceStatisticsResult:
        """构造空统计结果."""
        return InstanceStatisticsResult(
            total_instances=0,
            current_instances=0,
            active_instances=0,
            normal_instances=0,
            disabled_instances=0,
            deleted_instances=0,
            inactive_instances=0,
            audit_enabled_instances=0,
            high_availability_instances=0,
            managed_instances=0,
            unmanaged_instances=0,
            backed_up_instances=0,
            backup_stale_instances=0,
            not_backed_up_instances=0,
            backup_status_stats=_build_backup_status_stats({}),
            db_types_count=0,
            db_type_stats=[],
            port_stats=[],
            version_stats=[],
        )
