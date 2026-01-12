"""通用筛选器/下拉选项相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CommonInstanceOptionItem:
    """通用实例选项条目."""

    id: int
    name: str
    db_type: str
    display_name: str


@dataclass(slots=True)
class CommonInstancesOptionsResult:
    """通用实例选项结果."""

    instances: list[CommonInstanceOptionItem]


@dataclass(slots=True)
class CommonDatabasesOptionsFilters:
    """通用数据库选项查询参数."""

    instance_id: int
    limit: int
    offset: int


@dataclass(slots=True)
class CommonDatabaseOptionItem:
    """通用数据库选项条目."""

    id: int
    database_name: str
    is_active: bool
    first_seen_date: str | None
    last_seen_date: str | None
    deleted_at: str | None


@dataclass(slots=True)
class CommonDatabasesOptionsResult:
    """通用数据库选项结果."""

    databases: list[CommonDatabaseOptionItem]
    total_count: int
    limit: int
    offset: int


@dataclass(slots=True)
class CommonDatabaseTypeOptionItem:
    """通用数据库类型选项条目."""

    value: str
    text: str
    icon: str | None
    color: str | None


@dataclass(slots=True)
class CommonDatabaseTypesOptionsResult:
    """通用数据库类型选项结果."""

    options: list[CommonDatabaseTypeOptionItem]
