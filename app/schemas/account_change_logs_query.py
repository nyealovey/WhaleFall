"""账户变更日志（全量）相关 query/filter schema.

目标:
- 将 API 层 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.types.account_change_logs import AccountChangeLogsListFilters
from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_optional_int, parse_text

_ALLOWED_SORT_ORDERS = {"asc", "desc"}
_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200
_MAX_HOURS = 24 * 90


def _parse_optional_lower_text(value: Any) -> str | None:
    cleaned = parse_text(value)
    return cleaned.lower() if cleaned else None


def _resolve_hours(value: Any) -> int | None:
    parsed = parse_optional_int(value)
    if parsed is None:
        return None
    if parsed < 1:
        raise ValueError("hours 参数必须为正整数")
    return min(parsed, _MAX_HOURS)


class AccountChangeLogsListQuery(PayloadSchema):
    """账户变更日志列表 query 参数 schema."""

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    sort_field: str = Field(default="change_time", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))
    search: str = ""
    instance_id: int | None = Field(default=None, validation_alias=AliasChoices("instance_id", "instance"))
    db_type: str | None = None
    change_type: str | None = None
    status: str | None = None
    hours: int | None = None

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
        cleaned = parse_text(value).lower()
        return cleaned or "change_time"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        cleaned = parse_text(value).lower()
        if not cleaned:
            return "desc"
        if cleaned in _ALLOWED_SORT_ORDERS:
            return cleaned
        # COMPAT: 非法值降级为默认 desc.
        return "desc"

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        return parse_optional_int(value)

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        return _parse_optional_lower_text(value)

    @field_validator("change_type", mode="before")
    @classmethod
    def _parse_change_type(cls, value: Any) -> str | None:
        return _parse_optional_lower_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, value: Any) -> str | None:
        return _parse_optional_lower_text(value)

    @field_validator("hours", mode="before")
    @classmethod
    def _parse_hours(cls, value: Any) -> int | None:
        return _resolve_hours(value)

    def to_filters(self) -> AccountChangeLogsListFilters:
        """转换为列表查询 filters 对象."""
        return AccountChangeLogsListFilters(
            page=self.page,
            limit=self.limit,
            sort_field=self.sort_field,
            sort_order=self.sort_order,
            search_term=self.search,
            instance_id=self.instance_id,
            db_type=self.db_type,
            change_type=self.change_type,
            status=self.status,
            hours=self.hours,
        )


class AccountChangeLogStatisticsQuery(PayloadSchema):
    """账户变更日志统计 query 参数 schema."""

    hours: int | None = None

    @field_validator("hours", mode="before")
    @classmethod
    def _parse_hours(cls, value: Any) -> int | None:
        return _resolve_hours(value)
