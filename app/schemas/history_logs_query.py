"""历史日志相关 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.constants.system_constants import LogLevel
from app.core.types.history_logs import LogSearchFilters
from app.schemas.base import PayloadSchema

_ALLOWED_SORT_ORDERS = {"asc", "desc"}
_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200
_MAX_HOURS = 24 * 90


def _parse_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        raise TypeError("参数必须为整数")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped, 10)
        except ValueError as exc:
            raise ValueError("参数必须为整数") from exc
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("参数必须为整数") from exc


def _parse_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _parse_optional_iso_datetime(value: Any, *, param_name: str) -> datetime | None:
    cleaned = _parse_text(value)
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError(f"{param_name} 参数必须为 ISO 8601 时间字符串") from exc


def _resolve_hours(value: Any) -> int | None:
    if value is None:
        return None
    hours = _parse_int(value, default=0)
    if hours < 1:
        raise ValueError("hours 参数必须为正整数")
    return min(hours, _MAX_HOURS)


class HistoryLogsListQuery(PayloadSchema):
    """日志列表 query 参数 schema."""

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    sort_field: str = Field(default="timestamp", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))
    level: LogLevel | None = None
    module: str | None = None
    search: str = ""
    start_time: datetime | None = None
    end_time: datetime | None = None
    hours: int | None = None

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = _parse_int(value, default=_DEFAULT_PAGE)
        return max(parsed, 1)

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = _parse_int(value, default=_DEFAULT_LIMIT)
        return max(min(parsed, _MAX_LIMIT), 1)

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        cleaned = _parse_text(value).lower()
        return cleaned or "timestamp"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        cleaned = _parse_text(value).lower()
        if not cleaned:
            return "desc"
        if cleaned in _ALLOWED_SORT_ORDERS:
            return cleaned
        # COMPAT: 非法值降级为默认 desc.
        return "desc"

    @field_validator("level", mode="before")
    @classmethod
    def _parse_level(cls, value: Any) -> LogLevel | None:
        cleaned = _parse_text(value)
        if not cleaned:
            return None
        try:
            return LogLevel(cleaned.upper())
        except ValueError as exc:
            raise ValueError("日志级别参数无效") from exc

    @field_validator("module", mode="before")
    @classmethod
    def _parse_module(cls, value: Any) -> str | None:
        cleaned = _parse_text(value)
        return cleaned if cleaned else None

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search(cls, value: Any) -> str:
        return _parse_text(value)

    @field_validator("start_time", mode="before")
    @classmethod
    def _parse_start_time(cls, value: Any) -> datetime | None:
        return _parse_optional_iso_datetime(value, param_name="start_time")

    @field_validator("end_time", mode="before")
    @classmethod
    def _parse_end_time(cls, value: Any) -> datetime | None:
        return _parse_optional_iso_datetime(value, param_name="end_time")

    @field_validator("hours", mode="before")
    @classmethod
    def _parse_hours(cls, value: Any) -> int | None:
        return _resolve_hours(value)

    def to_filters(self) -> LogSearchFilters:
        return LogSearchFilters(
            page=self.page,
            limit=self.limit,
            sort_field=self.sort_field,
            sort_order=self.sort_order,
            level=self.level,
            module=self.module,
            search_term=self.search,
            start_time=self.start_time,
            end_time=self.end_time,
            hours=self.hours,
        )


class HistoryLogStatisticsQuery(PayloadSchema):
    """日志统计 query 参数 schema."""

    hours: int = 24

    @field_validator("hours", mode="before")
    @classmethod
    def _parse_hours(cls, value: Any) -> int:
        # `/statistics` 历史上默认 24h.
        resolved = _resolve_hours(value)
        if resolved is None:
            return 24
        return resolved
