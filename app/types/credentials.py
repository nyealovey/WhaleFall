"""凭据相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class SupportsCredentialListRow(Protocol):
    """凭据列表行所需的最小 ORM 接口(结构化协议)."""

    id: int
    name: str
    credential_type: str
    db_type: str | None
    username: str
    category_id: int | None
    created_at: datetime | None
    updated_at: datetime | None
    description: str | None
    is_active: bool

    def get_password_masked(self) -> str:  # pragma: no cover - protocol
        """返回掩码后的口令字符串."""
        ...


@dataclass(slots=True)
class CredentialListFilters:
    """凭据列表筛选条件."""

    page: int
    limit: int
    search: str
    credential_type: str | None
    db_type: str | None
    status: str | None
    tags: list[str]
    sort_field: str
    sort_order: str


@dataclass(slots=True)
class CredentialListRowProjection:
    """凭据列表查询投影结果(Repository 输出)."""

    credential: SupportsCredentialListRow
    instance_count: int


@dataclass(slots=True)
class CredentialListItem:
    """凭据列表单行结构."""

    id: int
    name: str
    credential_type: str
    db_type: str | None
    username: str
    category_id: int | None
    created_at: str | None
    updated_at: str | None
    password: str
    description: str | None
    is_active: bool
    instance_count: int
    created_at_display: str
