"""标签相关 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from app.core.types.tags import TagListFilters
from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_text

_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


class TagsListQuery(PayloadSchema):
    """标签列表 query 参数 schema."""

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    search: str = ""
    category: str = ""
    status: str = "all"

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

    @field_validator("search", "category", mode="before")
    @classmethod
    def _parse_strings(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, value: Any) -> str:
        cleaned = parse_text(value).lower()
        return cleaned or "all"

    def to_filters(self) -> TagListFilters:
        """转换为标签列表 filters 对象."""
        status_filter = self.status if self.status not in {"", "all"} else ""
        return TagListFilters(
            page=self.page,
            limit=self.limit,
            search=self.search,
            category=self.category,
            status_filter=status_filter,
        )


class TagOptionsQuery(PayloadSchema):
    """标签 options query 参数 schema."""

    category: str = ""

    @field_validator("category", mode="before")
    @classmethod
    def _parse_category(cls, value: Any) -> str:
        return parse_text(value)
