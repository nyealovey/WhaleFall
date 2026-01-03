"""账户权限详情相关类型定义(AccountsLedgersPage)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AccountLedgerPermissionAccount:
    """台账权限查询账户信息."""

    id: int
    username: str
    instance_name: str
    db_type: str


@dataclass(slots=True)
class AccountLedgerPermissions:
    """台账权限详情."""

    db_type: str
    username: str
    is_superuser: bool
    last_sync_time: str

    snapshot: dict[str, Any]


@dataclass(slots=True)
class AccountLedgerPermissionsResult:
    """台账权限详情结果."""

    permissions: AccountLedgerPermissions
    account: AccountLedgerPermissionAccount
