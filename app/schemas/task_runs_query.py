"""TaskRun Center query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 提供稳定、可测试的 filters 结构
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.types.task_runs import TaskRunsListFilters
from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_text

_ALLOWED_SORT_ORDERS = {"asc", "desc"}
_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _parse_sort_order(value: Any, *, default: str) -> str:
    cleaned = parse_text(value).lower()
    if not cleaned:
        return default
    if cleaned in _ALLOWED_SORT_ORDERS:
        return cleaned
    return default


class TaskRunsListFiltersQuery(PayloadSchema):
    """任务运行列表 query 参数 schema."""

    task_key: str = ""
    task_category: str = ""
    trigger_source: str = ""
    status: str = ""
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    sort_field: str = Field(default="started_at", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))

    @field_validator("task_key", "task_category", "trigger_source", "status", mode="before")
    @classmethod
    def _parse_strings(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        return max(parsed, 1)

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_LIMIT)
        return max(min(parsed, _MAX_LIMIT), 1)

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        cleaned = parse_text(value)
        return cleaned or "started_at"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        return _parse_sort_order(value, default="desc")

    def to_filters(self) -> TaskRunsListFilters:
        """转换为 Service/Repository 可复用的 filters 结构."""
        return TaskRunsListFilters(
            task_key=self.task_key,
            task_category=self.task_category,
            trigger_source=self.trigger_source,
            status=self.status,
            page=self.page,
            limit=self.limit,
            sort_field=self.sort_field,
            sort_order=self.sort_order,
        )
