"""数据库统计相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseDbTypeStat:
    """数据库按类型统计项."""

    db_type: str
    count: int


@dataclass(slots=True)
class DatabaseInstanceStat:
    """数据库按实例统计项."""

    instance_id: int
    instance_name: str
    db_type: str
    count: int


@dataclass(slots=True)
class DatabaseSyncStatusStat:
    """数据库同步状态统计项."""

    value: str
    label: str
    variant: str
    count: int


@dataclass(slots=True)
class DatabaseCapacityRanking:
    """数据库容量排行项."""

    instance_id: int
    instance_name: str
    db_type: str
    database_name: str
    size_mb: int
    size_label: str
    collected_at: str | None


@dataclass(slots=True)
class DatabaseStatisticsResult:
    """数据库统计页面/API 数据."""

    total_databases: int
    active_databases: int
    inactive_databases: int
    deleted_databases: int
    total_instances: int
    total_size_mb: int
    avg_size_mb: float
    max_size_mb: int
    db_type_stats: list[DatabaseDbTypeStat]
    instance_stats: list[DatabaseInstanceStat]
    sync_status_stats: list[DatabaseSyncStatusStat]
    capacity_rankings: list[DatabaseCapacityRanking]
