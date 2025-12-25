"""分区管理相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(slots=True)
class PartitionEntry:
    """单个分区条目."""

    name: str
    table: str
    table_type: str
    display_name: str
    size: str
    size_bytes: int
    record_count: int
    date: str
    status: str


@dataclass(slots=True)
class PartitionInfoSnapshot:
    """分区信息快照."""

    partitions: list[PartitionEntry]
    total_partitions: int
    total_size_bytes: int
    total_size: str
    total_records: int
    tables: list[str]
    status: str
    missing_partitions: list[str]


@dataclass(slots=True)
class PartitionStatusSnapshot:
    """分区状态快照."""

    status: str
    total_partitions: int
    total_size: str
    total_records: int
    missing_partitions: list[str]
    partitions: list[PartitionEntry]


@dataclass(slots=True)
class PeriodWindow:
    """核心指标查询窗口."""

    period_start: date
    period_end: date
    stats_start: date
    stats_end: date
    step_mode: str


@dataclass(slots=True)
class PartitionCoreMetricsResult:
    """核心聚合指标结果."""

    labels: list[str]
    datasets: list[dict[str, Any]]
    dataPointCount: int
    timeRange: str
    yAxisLabel: str
    chartTitle: str
    periodType: str
