"""历史日志 Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import Text, asc, cast as sa_cast, desc, distinct, func, or_
from sqlalchemy.orm import Query

from app import db
from app.constants.system_constants import LogLevel
from app.models.unified_log import UnifiedLog
from app.types.history_logs import LogSearchFilters
from app.types.listing import PaginatedResult
from app.utils.time_utils import time_utils


class HistoryLogsRepository:
    """历史日志查询 Repository."""

    def list_logs(self, filters: LogSearchFilters) -> PaginatedResult[UnifiedLog]:
        query: Query[Any] = cast(Query[Any], UnifiedLog.query)
        query = self._apply_time_filters(
            query,
            start_time=filters.start_time,
            end_time=filters.end_time,
            hours=filters.hours,
        )

        if filters.level:
            query = query.filter(UnifiedLog.level == filters.level)

        if filters.module:
            query = query.filter(UnifiedLog.module.like(f"%{filters.module}%"))

        if filters.search_term:
            search_filter = or_(
                UnifiedLog.message.like(f"%{filters.search_term}%"),
                sa_cast(UnifiedLog.context, Text).like(f"%{filters.search_term}%"),
            )
            query = query.filter(search_filter)

        query = self._apply_log_sorting(query, sort_field=filters.sort_field, sort_order=filters.sort_order)

        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

    @staticmethod
    def list_modules() -> list[str]:
        rows = db.session.query(distinct(UnifiedLog.module).label("module")).order_by(UnifiedLog.module).all()
        return [row.module for row in rows]

    @staticmethod
    def fetch_statistics(
        *,
        start_time: datetime,
    ) -> tuple[int, int, dict[str, int], list[tuple[str, int]]]:
        total_logs = UnifiedLog.query.filter(UnifiedLog.timestamp >= start_time).count()

        level_stats = (
            db.session.query(UnifiedLog.level, func.count(UnifiedLog.id).label("count"))
            .filter(UnifiedLog.timestamp >= start_time)
            .group_by(UnifiedLog.level)
            .all()
        )
        module_stats = (
            db.session.query(UnifiedLog.module, func.count(UnifiedLog.id).label("count"))
            .filter(UnifiedLog.timestamp >= start_time)
            .group_by(UnifiedLog.module)
            .order_by(func.count(UnifiedLog.id).desc())
            .limit(10)
            .all()
        )
        error_count = UnifiedLog.query.filter(
            UnifiedLog.timestamp >= start_time,
            UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
        ).count()

        level_counts = {level.value: int(count or 0) for level, count in level_stats}
        top_modules = [(module, int(count or 0)) for module, count in module_stats]
        return total_logs, error_count, level_counts, top_modules

    @staticmethod
    def get_log(log_id: int) -> UnifiedLog:
        return UnifiedLog.query.get_or_404(log_id)

    @staticmethod
    def _apply_time_filters(
        query: Query[Any],
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        hours: int | None,
    ) -> Query[Any]:
        updated_query = query
        if start_time:
            updated_query = updated_query.filter(UnifiedLog.timestamp >= start_time)
        if end_time:
            updated_query = updated_query.filter(UnifiedLog.timestamp <= end_time)
        if not start_time and not end_time:
            window_hours = hours if hours is not None else 24
            updated_query = updated_query.filter(
                UnifiedLog.timestamp >= time_utils.now() - timedelta(hours=window_hours),
            )
        return updated_query

    @staticmethod
    def _apply_log_sorting(query: Query[Any], *, sort_field: str, sort_order: str) -> Query[Any]:
        sortable_fields = {
            "id": UnifiedLog.id,
            "timestamp": UnifiedLog.timestamp,
            "level": UnifiedLog.level,
            "module": UnifiedLog.module,
            "message": UnifiedLog.message,
        }
        order_column = sortable_fields.get(sort_field, UnifiedLog.timestamp)
        return query.order_by(asc(order_column)) if sort_order == "asc" else query.order_by(desc(order_column))
