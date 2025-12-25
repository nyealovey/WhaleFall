"""账户权限详情相关类型定义(AccountsLedgersPage)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AccountLedgerPermissionAccount:
    id: int
    username: str
    instance_name: str
    db_type: str


@dataclass(slots=True)
class AccountLedgerPermissions:
    db_type: str
    username: str
    is_superuser: bool
    last_sync_time: str

    global_privileges: list[str] | None = None
    database_privileges: dict[str, Any] | None = None

    predefined_roles: list[str] | None = None
    role_attributes: dict[str, Any] | None = None
    database_privileges_pg: dict[str, Any] | None = None
    tablespace_privileges: dict[str, Any] | None = None

    server_roles: list[str] | None = None
    server_permissions: list[str] | None = None
    database_roles: dict[str, Any] | None = None
    database_permissions: dict[str, list[str]] | None = None

    oracle_roles: list[str] | None = None
    oracle_system_privileges: list[str] | None = None
    oracle_tablespace_privileges: dict[str, Any] | None = None


@dataclass(slots=True)
class AccountLedgerPermissionsResult:
    permissions: AccountLedgerPermissions
    account: AccountLedgerPermissionAccount

