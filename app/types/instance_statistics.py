"""实例统计相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class InstanceDbTypeStat:
    db_type: str
    count: int


@dataclass(slots=True)
class InstancePortStat:
    port: int | None
    count: int


@dataclass(slots=True)
class InstanceVersionStat:
    db_type: str
    version: str
    count: int


@dataclass(slots=True)
class InstanceStatisticsResult:
    """实例统计 API/页面数据."""

    total_instances: int
    active_instances: int
    normal_instances: int
    disabled_instances: int
    deleted_instances: int
    inactive_instances: int
    db_types_count: int
    db_type_stats: list[InstanceDbTypeStat]
    port_stats: list[InstancePortStat]
    version_stats: list[InstanceVersionStat]

