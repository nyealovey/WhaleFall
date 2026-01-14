"""同步会话(HistorySessionsPage) Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import NotFoundError
from app.core.types.history_sessions import HistorySessionsListFilters
from app.core.types.listing import PaginatedResult
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession


class HistorySessionsRepository:
    """同步会话查询 Repository."""

    def list_sessions(self, filters: HistorySessionsListFilters) -> PaginatedResult[SyncSession]:
        """分页查询同步会话."""
        started_at_column = cast("ColumnElement[Any]", SyncSession.started_at)
        completed_at_column = cast("ColumnElement[Any]", SyncSession.completed_at)
        status_column = cast(ColumnElement[str], SyncSession.status)
        sync_type_column = cast(ColumnElement[str], SyncSession.sync_type)
        sync_category_column = cast(ColumnElement[str], SyncSession.sync_category)

        sortable_fields = {
            "started_at": started_at_column,
            "completed_at": completed_at_column,
            "status": status_column,
        }
        sort_column = sortable_fields.get(filters.sort_field, started_at_column)
        ordering = sort_column.asc() if filters.sort_order == "asc" else sort_column.desc()

        query = SyncSession.query
        if filters.sync_type:
            query = query.filter(sync_type_column == filters.sync_type)
        if filters.sync_category:
            query = query.filter(sync_category_column == filters.sync_category)
        if filters.status:
            query = query.filter(status_column == filters.status)

        query = query.order_by(ordering, SyncSession.id.desc())
        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

    @staticmethod
    def get_session(session_id: str) -> SyncSession:
        """按 session_id 获取会话."""
        session = SyncSession.query.filter_by(session_id=session_id).first()
        if not session:
            msg = "会话不存在"
            raise NotFoundError(msg)
        return session

    @staticmethod
    def list_session_records(session_id: str) -> list[SyncInstanceRecord]:
        """列出会话的实例同步记录."""
        return SyncInstanceRecord.get_records_by_session(session_id)
