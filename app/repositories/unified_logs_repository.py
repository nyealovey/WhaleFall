"""统一日志(导出) Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import db
from app.models.unified_log import LogLevel, UnifiedLog


class UnifiedLogsRepository:
    """UnifiedLog 查询 Repository."""

    def __init__(self, *, session: Session | None = None) -> None:
        self._session = session or db.session

    def list_logs_for_export(
        self,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        level: LogLevel | None = None,
        module: str | None = None,
        limit: int = 1000,
    ) -> list[UnifiedLog]:
        query = self._session.query(UnifiedLog)

        if start_time is not None:
            query = query.filter(UnifiedLog.timestamp >= start_time)
        if end_time is not None:
            query = query.filter(UnifiedLog.timestamp <= end_time)
        if level is not None:
            query = query.filter(UnifiedLog.level == level)
        if module:
            query = query.filter(UnifiedLog.module.like(f"%{module}%"))

        normalized_limit = max(1, min(int(limit or 1000), 100000))
        return list(query.order_by(desc(UnifiedLog.timestamp)).limit(normalized_limit).all())
