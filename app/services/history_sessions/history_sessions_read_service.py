"""同步会话(HistorySessionsPage) read APIs Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from app.core.constants import SyncStatus
from app.core.types.history_sessions import (
    HistorySessionsListFilters,
    SyncInstanceRecordItem,
    SyncSessionDetailItem,
    SyncSessionDetailResult,
    SyncSessionErrorLogsResult,
    SyncSessionItem,
)
from app.core.types.listing import PaginatedResult
from app.repositories.history_sessions_repository import HistorySessionsRepository
from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1
from app.utils.structlog_config import get_system_logger


class HistorySessionsReadService:
    """同步会话读取服务."""

    def __init__(self, repository: HistorySessionsRepository | None = None) -> None:
        """初始化服务并注入会话仓库."""
        self._logger = get_system_logger()
        self._repository = repository or HistorySessionsRepository()

    def list_sessions(self, filters: HistorySessionsListFilters) -> PaginatedResult[SyncSessionItem]:
        """分页列出同步会话."""
        page_result = self._repository.list_sessions(filters)
        items: list[SyncSessionItem] = []
        for session in page_result.items:
            items.append(self._to_session_item(session))
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    def get_session_detail(self, session_id: str) -> SyncSessionDetailResult:
        """获取同步会话详情."""
        session = self._repository.get_session(session_id)
        records = self._repository.list_session_records(session_id)
        record_items = [self._to_record_item(record) for record in records]

        base = self._to_session_item(session)
        session_item = SyncSessionDetailItem(
            id=base.id,
            session_id=base.session_id,
            sync_type=base.sync_type,
            sync_category=base.sync_category,
            status=base.status,
            started_at=base.started_at,
            completed_at=base.completed_at,
            total_instances=base.total_instances,
            successful_instances=base.successful_instances,
            failed_instances=base.failed_instances,
            created_by=base.created_by,
            created_at=base.created_at,
            updated_at=base.updated_at,
            instance_records=record_items,
            progress_percentage=float(session.get_progress_percentage()),
        )
        return SyncSessionDetailResult(session=session_item)

    def get_session_error_logs(self, session_id: str) -> SyncSessionErrorLogsResult:
        """获取同步会话错误日志列表."""
        session = self._repository.get_session(session_id)
        records = self._repository.list_session_records(session_id)
        error_records = [record for record in records if getattr(record, "status", None) == SyncStatus.FAILED]
        error_items = [self._to_record_item(record) for record in error_records]
        return SyncSessionErrorLogsResult(
            session=self._to_session_item(session),
            error_records=error_items,
            error_count=len(error_items),
        )

    @staticmethod
    def _to_session_item(session: object) -> SyncSessionItem:
        resolved = cast("Any", session)
        return SyncSessionItem(
            id=int(getattr(resolved, "id", 0) or 0),
            session_id=str(getattr(resolved, "session_id", "") or ""),
            sync_type=str(getattr(resolved, "sync_type", "") or ""),
            sync_category=str(getattr(resolved, "sync_category", "") or ""),
            status=str(getattr(resolved, "status", "") or ""),
            started_at=(resolved.started_at.isoformat() if getattr(resolved, "started_at", None) else None),
            completed_at=(resolved.completed_at.isoformat() if getattr(resolved, "completed_at", None) else None),
            total_instances=int(getattr(resolved, "total_instances", 0) or 0),
            successful_instances=int(getattr(resolved, "successful_instances", 0) or 0),
            failed_instances=int(getattr(resolved, "failed_instances", 0) or 0),
            created_by=cast("int | None", getattr(resolved, "created_by", None)),
            created_at=(resolved.created_at.isoformat() if getattr(resolved, "created_at", None) else None),
            updated_at=(resolved.updated_at.isoformat() if getattr(resolved, "updated_at", None) else None),
        )

    def _to_record_item(self, record: object) -> SyncInstanceRecordItem:
        resolved = cast("Any", record)
        raw_sync_details = getattr(resolved, "sync_details", None)

        # COMPAT: 历史数据可能缺失 `sync_details.version`；统一在读入口补齐并记录命中。
        # EXIT: 在 backfill 迁移全量执行且观测窗口内无命中后，移除此兼容分支。
        if isinstance(raw_sync_details, dict):
            raw_version = raw_sync_details.get("version")
            if type(raw_version) is not int:
                self._logger.info(
                    "sync_details legacy payload normalized",
                    module="history_sessions",
                    fallback=True,
                    fallback_reason="SYNC_DETAILS_LEGACY_MISSING_VERSION",
                    session_id=str(getattr(resolved, "session_id", "") or ""),
                    record_id=int(getattr(resolved, "id", 0) or 0),
                    raw_version=raw_version,
                )

        try:
            sync_details = normalize_sync_details_v1(raw_sync_details)
        except Exception as exc:
            # fail-fast: 数据形状异常属于数据一致性问题，不应 silent fallback。
            self._logger.exception(
                "sync_details payload invalid",
                module="history_sessions",
                session_id=str(getattr(resolved, "session_id", "") or ""),
                record_id=int(getattr(resolved, "id", 0) or 0),
                error=str(exc),
            )
            raise

        return SyncInstanceRecordItem(
            id=int(getattr(resolved, "id", 0) or 0),
            session_id=str(getattr(resolved, "session_id", "") or ""),
            instance_id=int(getattr(resolved, "instance_id", 0) or 0),
            instance_name=cast("str | None", getattr(resolved, "instance_name", None)),
            sync_category=str(getattr(resolved, "sync_category", "") or ""),
            status=str(getattr(resolved, "status", "") or ""),
            started_at=(resolved.started_at.isoformat() if getattr(resolved, "started_at", None) else None),
            completed_at=(resolved.completed_at.isoformat() if getattr(resolved, "completed_at", None) else None),
            items_synced=int(getattr(resolved, "items_synced", 0) or 0),
            items_created=int(getattr(resolved, "items_created", 0) or 0),
            items_updated=int(getattr(resolved, "items_updated", 0) or 0),
            items_deleted=int(getattr(resolved, "items_deleted", 0) or 0),
            error_message=cast("str | None", getattr(resolved, "error_message", None)),
            sync_details=sync_details,
            created_at=(resolved.created_at.isoformat() if getattr(resolved, "created_at", None) else None),
        )
