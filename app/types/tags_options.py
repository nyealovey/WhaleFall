"""标签选项相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TagOptionItem:
    id: int
    name: str
    display_name: str
    category: str
    color: str
    color_value: str
    color_name: str
    css_class: str
    is_active: bool
    created_at: str | None
    updated_at: str | None


@dataclass(slots=True)
class TaggableInstance:
    id: int
    name: str
    host: str
    port: int | None
    db_type: str


@dataclass(slots=True)
class TagsBulkInstancesResult:
    instances: list[TaggableInstance]


@dataclass(slots=True)
class TagsBulkTagsResult:
    tags: list[TagOptionItem]
    category_names: dict[str, str]


@dataclass(slots=True)
class TagOptionsResult:
    tags: list[TagOptionItem]
    category: str | None
