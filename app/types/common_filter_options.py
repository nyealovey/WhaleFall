"""通用筛选器/下拉选项相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CommonInstanceOptionItem:
    id: int
    name: str
    db_type: str
    display_name: str


@dataclass(slots=True)
class CommonInstancesOptionsResult:
    instances: list[CommonInstanceOptionItem]


@dataclass(slots=True)
class CommonDatabasesOptionsFilters:
    instance_id: int
    limit: int
    offset: int


@dataclass(slots=True)
class CommonDatabaseOptionItem:
    id: int
    database_name: str
    is_active: bool
    first_seen_date: str | None
    last_seen_date: str | None
    deleted_at: str | None


@dataclass(slots=True)
class CommonDatabasesOptionsResult:
    databases: list[CommonDatabaseOptionItem]
    total_count: int
    limit: int
    offset: int


@dataclass(slots=True)
class CommonDatabaseTypeOptionItem:
    value: str
    text: str
    icon: str | None
    color: str | None


@dataclass(slots=True)
class CommonDatabaseTypesOptionsResult:
    options: list[CommonDatabaseTypeOptionItem]

