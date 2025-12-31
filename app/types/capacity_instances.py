"""容量统计(实例维度)相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.types.capacity_common import CapacityInstanceRef


@dataclass(slots=True)
class InstanceAggregationsFilters:
    """实例容量聚合列表筛选条件."""

    instance_id: int | None
    db_type: str | None
    period_type: str | None
    start_date: date | None
    end_date: date | None
    page: int
    limit: int
    get_all: bool


@dataclass(slots=True)
class InstanceAggregationsItem:
    """实例容量聚合单行结构."""

    id: int
    instance_id: int
    period_type: str
    period_start: str | None
    period_end: str | None

    total_size_mb: int
    avg_size_mb: int
    max_size_mb: int
    min_size_mb: int
    data_count: int

    database_count: int
    avg_database_count: float | None
    max_database_count: int | None
    min_database_count: int | None

    total_size_change_mb: int | None
    total_size_change_percent: float | None
    database_count_change: int | None
    database_count_change_percent: float | None
    growth_rate: float | None
    trend_direction: str | None

    calculated_at: str | None
    created_at: str | None

    instance: CapacityInstanceRef


@dataclass(slots=True)
class InstanceAggregationsListResult:
    """实例容量聚合列表响应结构(Service 输出 DTO)."""

    items: list[InstanceAggregationsItem]
    total: int
    page: int
    pages: int
    limit: int
    has_prev: bool
    has_next: bool


@dataclass(slots=True)
class InstanceAggregationsSummaryFilters:
    """实例容量汇总筛选条件."""

    instance_id: int | None
    db_type: str | None
    period_type: str | None
    start_date: date | None
    end_date: date | None


@dataclass(slots=True)
class InstanceAggregationsSummary:
    """实例容量汇总结构."""

    total_instances: int
    total_size_mb: int
    avg_size_mb: float
    max_size_mb: int
    period_type: str
    source: str
