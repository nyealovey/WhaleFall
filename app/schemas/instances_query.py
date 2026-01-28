"""实例相关 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.types.instances import InstanceListFilters
from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_tags, parse_text
from app.utils.payload_converters import as_bool

_ALLOWED_SORT_ORDERS = {"asc", "desc"}
_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _parse_sort_field(value: Any, *, default: str) -> str:
    cleaned = parse_text(value)
    if not cleaned:
        return default
    return cleaned.lower()


def _parse_sort_order(value: Any, *, default: str) -> str:
    cleaned = parse_text(value).lower()
    if not cleaned:
        return default
    if cleaned in _ALLOWED_SORT_ORDERS:
        return cleaned
    raise ValueError("sort_order 参数必须为 asc 或 desc")


class InstanceListFiltersQuery(PayloadSchema):
    """实例列表 query 参数 schema.

    用于将 API 层 `parse_args()` 输出收敛为稳定的 `InstanceListFilters`.
    """

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    sort_field: str = Field(default="id", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))
    search: str = ""
    db_type: str = ""
    status: str = ""
    tags: list[str] = Field(default_factory=list)
    include_deleted: bool = False

    @field_validator("page", mode="before")
    @classmethod
    def _parse_page(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_PAGE)
        if parsed < 1:
            raise ValueError("page 参数必须为正整数")
        return parsed

    @field_validator("limit", mode="before")
    @classmethod
    def _parse_limit(cls, value: Any) -> int:
        parsed = parse_int(value, default=_DEFAULT_LIMIT)
        if parsed < 1:
            raise ValueError("limit 参数必须为正整数")
        if parsed > _MAX_LIMIT:
            raise ValueError(f"limit 最大为 {_MAX_LIMIT}")
        return parsed

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        return _parse_sort_field(value, default="id")

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        return _parse_sort_order(value, default="desc")

    @field_validator("search", "db_type", "status", mode="before")
    @classmethod
    def _parse_strings(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, value: Any) -> list[str]:
        return parse_tags(value)

    @field_validator("include_deleted", mode="before")
    @classmethod
    def _parse_include_deleted(cls, value: Any) -> bool:
        return as_bool(value, default=False)

    def to_filters(self) -> InstanceListFilters:
        """转换为实例列表 filters 对象."""
        return InstanceListFilters(
            page=self.page,
            limit=self.limit,
            sort_field=self.sort_field,
            sort_order=self.sort_order,
            search=self.search,
            db_type=self.db_type,
            status=self.status,
            tags=list(self.tags),
            include_deleted=self.include_deleted,
        )


class InstancesOptionsQuery(PayloadSchema):
    """实例 options query 参数 schema."""

    db_type: str | None = None

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        cleaned = parse_text(value)
        return cleaned or None


class InstancesExportQuery(PayloadSchema):
    """实例导出 query 参数 schema."""

    search: str = ""
    db_type: str = ""

    @field_validator("search", "db_type", mode="before")
    @classmethod
    def _parse_export_params(cls, value: Any) -> str:
        return parse_text(value)
