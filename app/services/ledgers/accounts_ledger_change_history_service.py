"""账户台账-变更历史 Service.

职责:
- 基于 account_id(InstanceAccount.id) 返回账户变更历史
- 组织 repository 调用并输出稳定 DTO
- 不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import cast

from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.types.instance_accounts import (
    InstanceAccountChangeHistoryAccount,
    InstanceAccountChangeHistoryResult,
    InstanceAccountChangeLogItem,
)
from app.utils.time_utils import time_utils


class AccountsLedgerChangeHistoryService:
    """账户台账-变更历史读取服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        """初始化服务并注入台账仓库."""
        self._repository = repository or AccountsLedgerRepository()

    def get_change_history(self, account_id: int) -> InstanceAccountChangeHistoryResult:
        """获取账户变更历史."""
        account = self._repository.get_account_by_instance_account_id(account_id)
        username = cast(str, getattr(account, "username", ""))
        db_type = cast("str | None", getattr(account, "db_type", None))
        instance_id = cast(int, getattr(account, "instance_id", 0))

        change_logs = self._repository.list_change_logs(instance_id=instance_id, username=username, db_type=db_type)
        history_items: list[InstanceAccountChangeLogItem] = []
        for log_entry in change_logs:
            change_time = getattr(log_entry, "change_time", None)
            history_items.append(
                InstanceAccountChangeLogItem(
                    id=cast(int, getattr(log_entry, "id", 0)),
                    change_type=cast("str | None", getattr(log_entry, "change_type", None)),
                    change_time=(time_utils.format_china_time(change_time) if change_time else "未知"),
                    status=cast("str | None", getattr(log_entry, "status", None)),
                    message=cast("str | None", getattr(log_entry, "message", None)),
                    privilege_diff=getattr(log_entry, "privilege_diff", None),
                    other_diff=getattr(log_entry, "other_diff", None),
                    session_id=cast("str | None", getattr(log_entry, "session_id", None)),
                ),
            )

        return InstanceAccountChangeHistoryResult(
            account=InstanceAccountChangeHistoryAccount(
                id=account_id,
                username=username,
                db_type=db_type,
            ),
            history=history_items,
        )

