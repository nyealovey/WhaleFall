"""AccountsLedgersPage 权限详情 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import cast

from app.core.types.accounts_permissions import (
    AccountLedgerPermissionAccount,
    AccountLedgerPermissions,
    AccountLedgerPermissionsResult,
)
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.services.accounts_permissions.snapshot_view import build_permission_snapshot_view
from app.utils.time_utils import time_utils


class AccountsLedgerPermissionsService:
    """账户台账-权限详情读取服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        """初始化服务并注入台账仓库."""
        self._repository = repository or AccountsLedgerRepository()

    def get_permissions(self, account_id: int) -> AccountLedgerPermissionsResult:
        """获取账户权限详情."""
        account = self._repository.get_account_by_instance_account_id(account_id)
        instance = getattr(account, "instance", None)

        snapshot = build_permission_snapshot_view(account)

        permissions = AccountLedgerPermissions(
            db_type=cast(str, getattr(instance, "db_type", "")).upper(),
            username=cast(str, getattr(account, "username", "")),
            is_superuser=bool(getattr(account, "is_superuser", False)),
            last_sync_time=(
                time_utils.format_china_time(getattr(account, "last_sync_time", None))
                if getattr(account, "last_sync_time", None)
                else "未知"
            ),
            snapshot=snapshot,
        )

        account_payload = AccountLedgerPermissionAccount(
            id=cast(int, getattr(account, "instance_account_id", 0)),
            username=cast(str, getattr(account, "username", "")),
            instance_name=cast(str, getattr(instance, "name", None) or "未知实例"),
            db_type=cast(str, getattr(instance, "db_type", "")),
        )
        return AccountLedgerPermissionsResult(
            permissions=permissions,
            account=account_payload,
        )
