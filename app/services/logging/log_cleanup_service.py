"""日志与同步数据清理 Service.

职责:
- 组织 repository 调用并返回统计结果
- 不返回 Response、不 commit
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.repositories.log_cleanup_repository import LogCleanupRepository


@dataclass(frozen=True, slots=True)
class LogCleanupOutcome:
    """清理结果汇总."""

    deleted_logs: int
    deleted_sync_sessions: int
    deleted_sync_records: int


class LogCleanupService:
    """日志与同步数据清理服务."""

    def __init__(self, repository: LogCleanupRepository | None = None) -> None:
        self._repository = repository or LogCleanupRepository()

    def cleanup_before(self, cutoff_date: datetime) -> LogCleanupOutcome:
        """清理 cutoff_date 之前的数据."""
        deleted_logs = self._repository.delete_unified_logs_before(cutoff_date)
        deleted_sync_sessions = self._repository.delete_sync_sessions_before(cutoff_date)
        deleted_sync_records = self._repository.delete_sync_instance_records_before(cutoff_date)
        return LogCleanupOutcome(
            deleted_logs=deleted_logs,
            deleted_sync_sessions=deleted_sync_sessions,
            deleted_sync_records=deleted_sync_records,
        )

