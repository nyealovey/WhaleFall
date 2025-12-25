"""用户相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class UserListFilters:
    """用户列表筛选条件."""

    page: int
    limit: int
    search: str
    role: str | None
    status: str | None
    sort_field: str
    sort_order: str


@dataclass(slots=True)
class UserListItem:
    """用户列表单行结构."""

    id: int
    username: str
    role: str
    created_at: str | None
    created_at_display: str | None
    last_login: str | None
    is_active: bool
