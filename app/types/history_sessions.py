"""同步会话(HistorySessionsPage)相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class HistorySessionsListFilters:
    sync_type: str
    sync_category: str
    status: str
    page: int
    limit: int
    sort_field: str
    sort_order: str


@dataclass(slots=True)
class SyncSessionItem:
    id: int
    session_id: str
    sync_type: str
    sync_category: str
    status: str
    started_at: str | None
    completed_at: str | None
    total_instances: int
    successful_instances: int
    failed_instances: int
    created_by: int | None
    created_at: str | None
    updated_at: str | None


@dataclass(slots=True)
class SyncInstanceRecordItem:
    id: int
    session_id: str
    instance_id: int
    instance_name: str | None
    sync_category: str
    status: str
    started_at: str | None
    completed_at: str | None
    items_synced: int
    items_created: int
    items_updated: int
    items_deleted: int
    error_message: str | None
    sync_details: Any
    created_at: str | None


@dataclass(slots=True)
class SyncSessionDetailItem(SyncSessionItem):
    instance_records: list[SyncInstanceRecordItem]
    progress_percentage: float


@dataclass(slots=True)
class SyncSessionDetailResult:
    session: SyncSessionDetailItem


@dataclass(slots=True)
class SyncSessionErrorLogsResult:
    session: SyncSessionItem
    error_records: list[SyncInstanceRecordItem]
    error_count: int
