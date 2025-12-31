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

    snapshot: dict[str, Any]


@dataclass(slots=True)
class AccountLedgerPermissionsResult:
    permissions: AccountLedgerPermissions
    account: AccountLedgerPermissionAccount
