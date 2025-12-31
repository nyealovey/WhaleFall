"""实例详情-账户相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class InstanceAccountListFilters:
    """实例账户列表筛选条件."""

    instance_id: int
    include_deleted: bool
    include_permissions: bool
    search: str
    page: int
    limit: int
    sort_field: str
    sort_order: str


@dataclass(slots=True)
class InstanceAccountSummary:
    """实例账户汇总信息."""

    total: int
    active: int
    deleted: int
    superuser: int


@dataclass(slots=True)
class InstanceAccountListItem:
    """实例账户列表单行结构."""

    id: int
    username: str
    is_superuser: bool
    is_locked: bool
    is_deleted: bool
    last_change_time: str | None
    type_specific: dict[str, Any]

    host: str | None = None
    plugin: str | None = None
    password_change_time: str | None = None
    oracle_id: int | str | None = None
    authentication_type: str | None = None
    account_status: str | None = None
    lock_date: str | None = None
    expiry_date: str | None = None
    default_tablespace: str | None = None
    created: str | None = None

    server_roles: list[str] | None = None
    server_permissions: list[str] | None = None
    database_roles: dict[str, Any] | None = None
    database_permissions: dict[str, Any] | None = None


@dataclass(slots=True)
class InstanceAccountListResult:
    """实例账户列表响应结构(Service 输出 DTO)."""

    items: list[InstanceAccountListItem]
    total: int
    page: int
    pages: int
    limit: int
    summary: InstanceAccountSummary


@dataclass(slots=True)
class InstanceAccountInfo:
    """权限详情中的账户信息."""

    id: int
    instance_id: int
    username: str
    instance_name: str | None
    db_type: str | None


@dataclass(slots=True)
class InstanceAccountPermissions:
    """权限详情结构(包含不同数据库类型的差异字段)."""

    db_type: str
    username: str
    is_superuser: bool
    last_sync_time: str

    snapshot: dict[str, Any]


@dataclass(slots=True)
class InstanceAccountPermissionsResult:
    """账户权限详情响应结构(Service 输出 DTO)."""

    permissions: InstanceAccountPermissions
    account: InstanceAccountInfo


@dataclass(slots=True)
class InstanceAccountChangeLogItem:
    """账户变更历史单条记录."""

    id: int
    change_type: str | None
    change_time: str
    status: str | None
    message: str | None
    privilege_diff: Any
    other_diff: Any
    session_id: str | None


@dataclass(slots=True)
class InstanceAccountChangeHistoryAccount:
    """变更历史中的账户信息."""

    id: int
    username: str
    db_type: str | None


@dataclass(slots=True)
class InstanceAccountChangeHistoryResult:
    """账户变更历史响应结构(Service 输出 DTO)."""

    account: InstanceAccountChangeHistoryAccount
    history: list[InstanceAccountChangeLogItem]
