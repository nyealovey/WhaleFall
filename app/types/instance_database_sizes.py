"""实例详情-数据库容量(大小)相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class InstanceDatabaseSizesQuery:
    """实例数据库容量查询参数."""

    instance_id: int
    database_name: str | None
    start_date: date | None
    end_date: date | None
    include_inactive: bool
    limit: int
    offset: int


@dataclass(slots=True)
class InstanceDatabaseSizeEntry:
    """单条数据库容量记录(最新或历史)."""

    id: int | None
    database_name: str
    size_mb: int | float | None
    data_size_mb: int | float | None
    log_size_mb: int | float | None
    collected_date: str | None
    collected_at: str | None
    is_active: bool
    deleted_at: str | None
    last_seen_date: str | None


@dataclass(slots=True)
class InstanceDatabaseSizesLatestResult:
    """最新容量统计结果."""

    total: int
    limit: int
    offset: int
    active_count: int
    filtered_count: int
    total_size_mb: int | float
    databases: list[InstanceDatabaseSizeEntry]


@dataclass(slots=True)
class InstanceDatabaseSizesHistoryResult:
    """历史容量统计结果."""

    total: int
    limit: int
    offset: int
    databases: list[InstanceDatabaseSizeEntry]

