"""容量统计(数据库维度)相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.types.capacity_common import CapacityInstanceRef


@dataclass(slots=True)
class DatabaseAggregationsFilters:
    """数据库容量聚合列表筛选条件."""

    instance_id: int | None
    db_type: str | None
    database_name: str | None
    database_id: int | None
    period_type: str | None
    start_date: date | None
    end_date: date | None
    page: int
    limit: int
    get_all: bool


@dataclass(slots=True)
class DatabaseAggregationsItem:
    """数据库容量聚合单行结构."""

    id: int
    instance_id: int
    database_name: str
    period_type: str
    period_start: str | None
    period_end: str | None

    avg_size_mb: int
    max_size_mb: int
    min_size_mb: int
    data_count: int

    avg_data_size_mb: int | None
    max_data_size_mb: int | None
    min_data_size_mb: int | None
    avg_log_size_mb: int | None
    max_log_size_mb: int | None
    min_log_size_mb: int | None

    size_change_mb: int
    size_change_percent: float
    data_size_change_mb: int | None
    data_size_change_percent: float | None
    log_size_change_mb: int | None
    log_size_change_percent: float | None
    growth_rate: float

    calculated_at: str | None
    created_at: str | None

    instance: CapacityInstanceRef


@dataclass(slots=True)
class DatabaseAggregationsListResult:
    """数据库容量聚合列表响应结构(Service 输出 DTO)."""

    items: list[DatabaseAggregationsItem]
    total: int
    page: int
    pages: int
    limit: int
    has_prev: bool
    has_next: bool


@dataclass(slots=True)
class DatabaseAggregationsSummaryFilters:
    """数据库容量汇总筛选条件."""

    instance_id: int | None
    db_type: str | None
    database_name: str | None
    database_id: int | None
    period_type: str | None
    start_date: date | None
    end_date: date | None


@dataclass(slots=True)
class DatabaseAggregationsSummary:
    """数据库容量汇总结构."""

    total_databases: int
    total_instances: int
    total_size_mb: int
    avg_size_mb: float
    max_size_mb: int
    growth_rate: float
