"""凭据相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.credential import Credential


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

    credential: Credential
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
