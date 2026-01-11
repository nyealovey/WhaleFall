"""日志与同步数据清理 Repository.

职责:
- 仅负责 Query 组装与数据库写入(delete)
- 不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime

from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.models.unified_log import UnifiedLog


class LogCleanupRepository:
    """日志与同步数据清理仓库."""

    @staticmethod
    def delete_unified_logs_before(cutoff_date: datetime) -> int:
        """删除 cutoff_date 之前的统一日志."""
        return int(
            UnifiedLog.query.filter(UnifiedLog.timestamp < cutoff_date).delete(synchronize_session=False) or 0,
        )

    @staticmethod
    def delete_sync_sessions_before(cutoff_date: datetime) -> int:
        """删除 cutoff_date 之前的同步会话."""
        return int(
            SyncSession.query.filter(SyncSession.created_at < cutoff_date).delete(synchronize_session=False) or 0,
        )

    @staticmethod
    def delete_sync_instance_records_before(cutoff_date: datetime) -> int:
        """删除 cutoff_date 之前的同步实例记录."""
        return int(
            SyncInstanceRecord.query.filter(SyncInstanceRecord.created_at < cutoff_date).delete(
                synchronize_session=False,
            )
            or 0,
        )

