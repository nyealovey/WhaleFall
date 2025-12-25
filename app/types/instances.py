"""实例相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class InstanceListFilters:
    """实例列表筛选条件."""

    page: int
    limit: int
    sort_field: str
    sort_order: str
    search: str
    db_type: str
    status: str
    tags: list[str]
    include_deleted: bool


@dataclass(slots=True)
class InstanceTagSummary:
    """实例列表 Tag 展示结构."""

    name: str
    display_name: str
    color: str


@dataclass(slots=True)
class InstanceListMetrics:
    """实例列表聚合信息(供 Service 组装 DTO 使用)."""

    database_counts: dict[int, int]
    account_counts: dict[int, int]
    last_sync_times: dict[int, datetime]
    tags_map: dict[int, list[InstanceTagSummary]]


@dataclass(slots=True)
class InstanceListItem:
    """实例列表单行结构."""

    id: int
    name: str
    db_type: str
    host: str
    port: int
    description: str
    is_active: bool
    deleted_at: str | None
    status: str
    main_version: str | None
    active_db_count: int
    active_account_count: int
    last_sync_time: str | None
    tags: list[InstanceTagSummary]

