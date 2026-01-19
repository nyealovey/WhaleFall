"""同步会话 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.types.history_sessions import HistorySessionsListFilters
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
    # COMPAT: 维持旧行为 - 非法 sort_order 降级为默认值,避免接口行为变更为 400.
    return default


class HistorySessionsListFiltersQuery(PayloadSchema):
    """同步会话列表 query 参数 schema.

    用于将 API 层 `parse_args()` 输出收敛为稳定的 `HistorySessionsListFilters`.
    """

    sync_type: str = ""
    sync_category: str = ""
    status: str = ""
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    sort_field: str = Field(default="started_at", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))

    @field_validator("sync_type", "sync_category", "status", mode="before")
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

    def to_filters(self) -> HistorySessionsListFilters:
        """转换为历史会话查询 filters 对象."""
        return HistorySessionsListFilters(
            sync_type=self.sync_type,
            sync_category=self.sync_category,
            status=self.status,
            page=self.page,
            limit=self.limit,
            sort_field=self.sort_field,
            sort_order=self.sort_order,
        )
