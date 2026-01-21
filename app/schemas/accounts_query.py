"""账户台账相关 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.types.accounts_ledgers import AccountFilters
from app.schemas.base import PayloadSchema
from app.schemas.query_parsers import parse_int, parse_tags, parse_text
from app.utils.payload_converters import as_bool

_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


class AccountsFiltersQuery(PayloadSchema):
    """账户台账筛选 query 参数 schema."""

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    search: str = ""
    instance_id: int | None = None
    include_deleted: bool = False
    include_roles: bool = False
    is_locked: str | None = None
    is_superuser: str | None = None
    plugin: str = ""
    tags: list[str] = Field(default_factory=list)
    classification: str = ""
    db_type: str | None = None

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

    @field_validator("search", "plugin", "classification", mode="before")
    @classmethod
    def _parse_strings(cls, value: Any) -> str:
        return parse_text(value)

    @field_validator("instance_id", mode="before")
    @classmethod
    def _parse_instance_id(cls, value: Any) -> int | None:
        if value is None:
            return None
        parsed = parse_int(value, default=0)
        return parsed if parsed > 0 else None

    @field_validator("include_deleted", "include_roles", mode="before")
    @classmethod
    def _parse_boolean_flags(cls, value: Any) -> bool:
        return as_bool(value, default=False)

    @field_validator("is_locked", "is_superuser", mode="before")
    @classmethod
    def _parse_lock_filters(cls, value: Any) -> str | None:
        cleaned = parse_text(value).lower()
        return cleaned if cleaned in {"true", "false"} else None

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, value: Any) -> list[str]:
        return parse_tags(value)

    @field_validator("db_type", mode="before")
    @classmethod
    def _parse_db_type(cls, value: Any) -> str | None:
        cleaned = parse_text(value).lower()
        if not cleaned or cleaned == "all":
            return None
        return cleaned

    def to_filters(self) -> AccountFilters:
        """转换为账户筛选 filters 对象."""
        classification_filter = self.classification if self.classification not in {"", "all"} else ""
        return AccountFilters(
            page=self.page,
            limit=self.limit,
            search=self.search,
            instance_id=self.instance_id,
            include_deleted=self.include_deleted,
            include_roles=self.include_roles,
            is_locked=self.is_locked,
            is_superuser=self.is_superuser,
            plugin=self.plugin,
            tags=list(self.tags),
            classification=self.classification,
            classification_filter=classification_filter,
            db_type=self.db_type,
        )


class AccountsLedgersListQuery(AccountsFiltersQuery):
    """账户台账列表 query 参数 schema."""

    sort_field: str = Field(default="username", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="asc", validation_alias=AliasChoices("order", "sort_order"))

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        cleaned = parse_text(value)
        return cleaned or "username"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        cleaned = parse_text(value).lower()
        return cleaned or "asc"
