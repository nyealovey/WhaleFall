"""实例详情-数据库表容量相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class InstanceDatabaseTableSizesQuery:
    """实例数据库表容量查询参数."""

    instance_id: int
    database_name: str
    schema_name: str | None
    table_name: str | None
    limit: int
    offset: int


@dataclass(slots=True)
class InstanceDatabaseTableSizeEntry:
    """单条表容量记录."""

    schema_name: str
    table_name: str
    size_mb: int | float | None
    data_size_mb: int | float | None
    index_size_mb: int | float | None
    row_count: int | None
    collected_at: str | None


@dataclass(slots=True)
class InstanceDatabaseTableSizesResult:
    """表容量快照查询结果."""

    total: int
    limit: int
    offset: int
    collected_at: str | None
    tables: list[InstanceDatabaseTableSizeEntry]
