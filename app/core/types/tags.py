"""标签相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class SupportsTagListRow(Protocol):
    """标签列表行所需的最小 ORM 接口(结构化协议)."""

    id: int
    name: str
    display_name: str
    category: str
    color: str
    color_value: str
    color_name: str
    css_class: str
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None


@dataclass(slots=True)
class TagSummary:
    """通用标签展示结构."""

    name: str
    display_name: str
    color: str


@dataclass(slots=True)
class TagListFilters:
    """标签列表筛选条件."""

    page: int
    limit: int
    search: str
    category: str
    status_filter: str


@dataclass(slots=True)
class TagListRowProjection:
    """标签列表查询投影结果(Repository 输出)."""

    tag: SupportsTagListRow
    instance_count: int


@dataclass(slots=True)
class TagStats:
    """标签统计信息."""

    total: int
    active: int
    inactive: int
    category_count: int


@dataclass(slots=True)
class TagListItem:
    """标签列表单行结构."""

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
    instance_count: int
