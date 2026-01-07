"""台账相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.types.tags import TagSummary


@dataclass(slots=True)
class DatabaseLedgerFilters:
    """数据库台账筛选条件."""

    search: str
    db_type: str
    tags: list[str]
    instance_id: int | None
    page: int
    per_page: int


@dataclass(slots=True)
class DatabaseLedgerRowProjection:
    """数据库台账查询投影结果(Repository 输出)."""

    id: int
    database_name: str
    instance_id: int
    instance_name: str
    instance_host: str
    db_type: str
    collected_at: datetime | None
    size_mb: int | None
    tags: list[TagSummary]


@dataclass(slots=True)
class DatabaseLedgerInstanceSummary:
    """数据库台账行的实例信息."""

    id: int
    name: str
    host: str
    db_type: str


@dataclass(slots=True)
class DatabaseLedgerCapacitySummary:
    """数据库台账行的容量信息."""

    size_mb: int | None
    size_bytes: int | None
    label: str
    collected_at: str | None


@dataclass(slots=True)
class DatabaseLedgerSyncStatusSummary:
    """数据库台账行的同步状态."""

    value: str
    label: str
    variant: str


@dataclass(slots=True)
class DatabaseLedgerItem:
    """数据库台账单行结构."""

    id: int
    database_name: str
    instance: DatabaseLedgerInstanceSummary
    db_type: str
    capacity: DatabaseLedgerCapacitySummary
    sync_status: DatabaseLedgerSyncStatusSummary
    tags: list[TagSummary]


@dataclass(slots=True)
class DatabaseCapacityTrendPoint:
    """数据库容量趋势单点."""

    collected_at: str | None
    collected_date: str | None
    size_mb: int | None
    size_bytes: int | None
    label: str


@dataclass(slots=True)
class DatabaseCapacityTrendDatabase:
    """容量趋势中的数据库元信息."""

    id: int
    name: str
    instance_id: int
    instance_name: str
    db_type: str


@dataclass(slots=True)
class DatabaseCapacityTrendResult:
    """容量趋势响应结构(Service 输出 DTO)."""

    database: DatabaseCapacityTrendDatabase
    points: list[DatabaseCapacityTrendPoint]
