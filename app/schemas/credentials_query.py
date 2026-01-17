"""凭据相关 query/filter schema.

目标:
- 将 API 层的 query 参数规范化/默认值/边界处理下沉到 schema 单入口
- 避免 `or` truthy 兜底链覆盖合法 falsy 值,并提供可测试的 canonicalization
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, Field, field_validator

from app.core.types.credentials import CredentialListFilters
from app.schemas.base import PayloadSchema

_ALLOWED_SORT_ORDERS = {"asc", "desc"}
_DEFAULT_PAGE = 1
_DEFAULT_LIMIT = 20
_MAX_LIMIT = 200


def _parse_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    # bool 是 int 的子类,分页参数不应接受 bool.
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


def _parse_choice(value: Any) -> str | None:
    cleaned = _parse_text(value)
    if not cleaned:
        return None
    if cleaned.lower() == "all":
        return None
    return cleaned


def _parse_status(value: Any) -> str | None:
    cleaned = _parse_text(value).lower()
    if cleaned in {"active", "inactive"}:
        return cleaned
    return None


def _parse_sort_order(value: Any, *, default: str) -> str:
    cleaned = _parse_text(value).lower()
    if not cleaned:
        return default
    if cleaned in _ALLOWED_SORT_ORDERS:
        return cleaned
    # COMPAT: 维持旧行为 - 非法 sort_order 降级为默认值,避免接口行为变更为 400.
    return default


def _parse_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            cleaned = item.strip()
            if cleaned:
                result.append(cleaned)
        return result
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


class CredentialListFiltersQuery(PayloadSchema):
    """凭据列表 query 参数 schema.

    用于将 API 层 `parse_args()` 输出收敛为稳定的 `CredentialListFilters`.
    """

    page: int = _DEFAULT_PAGE
    limit: int = _DEFAULT_LIMIT
    search: str = ""
    credential_type: str | None = None
    db_type: str | None = None
    status: str | None = None
    tags: list[str] = Field(default_factory=list)
    sort_field: str = Field(default="created_at", validation_alias=AliasChoices("sort", "sort_field"))
    sort_order: str = Field(default="desc", validation_alias=AliasChoices("order", "sort_order"))

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

    @field_validator("search", mode="before")
    @classmethod
    def _parse_search(cls, value: Any) -> str:
        return _parse_text(value)

    @field_validator("credential_type", "db_type", mode="before")
    @classmethod
    def _parse_choice(cls, value: Any) -> str | None:
        return _parse_choice(value)

    @field_validator("status", mode="before")
    @classmethod
    def _parse_status(cls, value: Any) -> str | None:
        return _parse_status(value)

    @field_validator("tags", mode="before")
    @classmethod
    def _parse_tags(cls, value: Any) -> list[str]:
        return _parse_tags(value)

    @field_validator("sort_field", mode="before")
    @classmethod
    def _parse_sort_field(cls, value: Any) -> str:
        cleaned = _parse_text(value).lower()
        return cleaned or "created_at"

    @field_validator("sort_order", mode="before")
    @classmethod
    def _parse_sort_order(cls, value: Any) -> str:
        return _parse_sort_order(value, default="desc")

    def to_filters(self) -> CredentialListFilters:
        return CredentialListFilters(
            page=self.page,
            limit=self.limit,
            search=self.search,
            credential_type=self.credential_type,
            db_type=self.db_type,
            status=self.status,
            tags=list(self.tags),
            sort_field=self.sort_field,
            sort_order=self.sort_order,
        )
