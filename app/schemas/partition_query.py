"""分区相关 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_text

_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


class PartitionsListQuery(PayloadSchema):
    """分区列表 query 参数 schema."""

    search: str = ""
    table_type: str = ""
    status: str = ""
    sort_field: str = Field(default="name", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="asc", validation_alias=AliasChoices("order", "sort_order"))
    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT

    @field_validator("search", "table_type", "status", mode="before")
    @classmethod
    def _parse_strings(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        cleaned = parse_text(value)
        return cleaned or "name"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        cleaned = parse_text(value)
        return cleaned or "asc"

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        # COMPAT: page=0 时沿用旧逻辑降级到默认 1.
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        return max(parsed, 1)

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        # COMPAT: limit=0 时沿用旧逻辑降级到默认 20.
        parsed = parse_int(value, default=_DEFAULT_LIMIT)
        return max(min(parsed, _MAX_LIMIT), 1)


class PartitionCoreMetricsQuery(PayloadSchema):
    """分区 core-metrics query 参数 schema."""

    period_type: str = "daily"
    days: int = 7

    @field_validator("period_type", mode="before")
    @classmethod
    def _parse_period_type(cls, value: Any) -> str:
        cleaned = parse_text(value).lower()
        return cleaned or "daily"

    @field_validator("days", mode="before")
    @classmethod
    def _parse_days(cls, value: Any) -> int:
        # COMPAT: days=0 时沿用旧逻辑降级到默认 7.
        if value == 0:
            return 7
        return parse_int(value, default=7)
