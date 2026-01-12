"""容量采集状态 Service.

职责:
- 组织 repository 调用并输出稳定结构
- 不做 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.repositories.capacity_collection_status_repository import CapacityCollectionStatusRepository


@dataclass(frozen=True, slots=True)
class CapacityCollectionStatus:
    """容量采集状态."""

    total_records: int
    today_records: int
    latest_collection: datetime | None


class CapacityCollectionStatusService:
    """容量采集状态读取服务."""

    def __init__(self, repository: CapacityCollectionStatusRepository | None = None) -> None:
        self._repository = repository or CapacityCollectionStatusRepository()

    def get_status(self, *, today: date) -> CapacityCollectionStatus:
        """获取采集状态."""
        total_stats = self._repository.count_all_stats()
        today_stats = self._repository.count_stats_since(since_date=today)
        latest_stat = self._repository.get_latest_stat()
        latest_time = latest_stat.created_at if latest_stat else None
        return CapacityCollectionStatus(
            total_records=total_stats,
            today_records=today_stats,
            latest_collection=latest_time,
        )

