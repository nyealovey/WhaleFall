"""实例统计 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import cast

from app.repositories.instance_statistics_repository import InstanceStatisticsRepository
from app.types.instance_statistics import (
    InstanceDbTypeStat,
    InstancePortStat,
    InstanceStatisticsResult,
    InstanceVersionStat,
)


class InstanceStatisticsReadService:
    """实例统计读取服务."""

    def __init__(self, repository: InstanceStatisticsRepository | None = None) -> None:
        self._repository = repository or InstanceStatisticsRepository()

    def build_statistics(self) -> InstanceStatisticsResult:
        totals = self._repository.fetch_summary()
        db_type_rows = self._repository.fetch_db_type_stats()
        port_rows = self._repository.fetch_port_stats()
        version_rows = self._repository.fetch_version_stats()

        db_type_stats = [
            InstanceDbTypeStat(
                db_type=cast(str, getattr(row, "db_type", "")),
                count=int(getattr(row, "count", 0) or 0),
            )
            for row in db_type_rows
        ]
        port_stats = [
            InstancePortStat(
                port=cast("int | None", getattr(row, "port", None)),
                count=int(getattr(row, "count", 0) or 0),
            )
            for row in port_rows
        ]
        version_stats = [
            InstanceVersionStat(
                db_type=cast(str, getattr(row, "db_type", "")),
                version=cast(str, getattr(row, "main_version", None) or "未知版本"),
                count=int(getattr(row, "count", 0) or 0),
            )
            for row in version_rows
        ]

        return InstanceStatisticsResult(
            total_instances=totals["total_instances"],
            active_instances=totals["active_instances"],
            normal_instances=totals["normal_instances"],
            disabled_instances=totals["disabled_instances"],
            deleted_instances=totals["deleted_instances"],
            inactive_instances=totals["disabled_instances"],
            db_types_count=len(db_type_rows),
            db_type_stats=db_type_stats,
            port_stats=port_stats,
            version_stats=version_stats,
        )

    @staticmethod
    def empty_statistics() -> InstanceStatisticsResult:
        return InstanceStatisticsResult(
            total_instances=0,
            active_instances=0,
            normal_instances=0,
            disabled_instances=0,
            deleted_instances=0,
            inactive_instances=0,
            db_types_count=0,
            db_type_stats=[],
            port_stats=[],
            version_stats=[],
        )
