"""标签选项相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TagOptionItem:
    """标签下拉选项项."""

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
    """可打标签的实例摘要."""

    id: int
    name: str
    host: str
    port: int | None
    db_type: str


@dataclass(slots=True)
class TagsBulkInstancesResult:
    """批量标签实例列表结果."""

    instances: list[TaggableInstance]


@dataclass(slots=True)
class TagsBulkTagsResult:
    """批量标签标签列表结果."""

    tags: list[TagOptionItem]
    category_names: dict[str, str]


@dataclass(slots=True)
class TagOptionsResult:
    """标签下拉选项结果."""

    tags: list[TagOptionItem]
    category: str | None
