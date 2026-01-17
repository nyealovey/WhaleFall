"""AccountsLedgersPage 权限详情 Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

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
        instance = account.instance

        snapshot = build_permission_snapshot_view(account)

        permissions = AccountLedgerPermissions(
            db_type=instance.db_type.upper(),
            username=account.username,
            is_superuser=account.is_superuser,
            last_sync_time=(time_utils.format_china_time(account.last_sync_time) if account.last_sync_time else "未知"),
            snapshot=snapshot,
        )

        account_payload = AccountLedgerPermissionAccount(
            id=account.instance_account_id,
            username=account.username,
            instance_name=instance.name or "未知实例",
            db_type=instance.db_type,
        )
        return AccountLedgerPermissionsResult(
            permissions=permissions,
            account=account_payload,
        )
