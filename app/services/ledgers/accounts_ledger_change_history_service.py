"""账户台账-变更历史 Service.

职责:
- 基于 account_id(InstanceAccount.id) 返回账户变更历史
- 组织 repository 调用并输出稳定 DTO
- 不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import cast

from app.core.types.instance_accounts import (
    InstanceAccountChangeHistoryAccount,
    InstanceAccountChangeHistoryResult,
    InstanceAccountChangeLogItem,
)
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.schemas.internal_contracts.account_change_log_diff_v1 import extract_diff_entries
from app.utils.structlog_config import get_system_logger
from app.utils.time_utils import time_utils


class AccountsLedgerChangeHistoryService:
    """账户台账-变更历史读取服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        """初始化服务并注入台账仓库."""
        self._logger = get_system_logger()
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
            raw_privilege_diff = getattr(log_entry, "privilege_diff", None)
            raw_other_diff = getattr(log_entry, "other_diff", None)

            # COMPAT: 历史数据为 legacy list 形状；读入口统一收敛为 list 并记录命中。
            # EXIT: 在 backfill 迁移全量执行且观测窗口内无命中后，移除此兼容分支。
            if isinstance(raw_privilege_diff, list) or isinstance(raw_other_diff, list):
                self._logger.info(
                    "account_change_log diff legacy list normalized",
                    module="accounts_ledger_change_history_service",
                    fallback=True,
                    fallback_reason="ACCOUNT_CHANGE_LOG_DIFF_LEGACY_LIST",
                    account_id=account_id,
                    instance_id=instance_id,
                )

            try:
                privilege_diff = extract_diff_entries(raw_privilege_diff)
                other_diff = extract_diff_entries(raw_other_diff)
            except Exception as exc:
                self._logger.exception(
                    "account_change_log diff payload invalid",
                    module="accounts_ledger_change_history_service",
                    account_id=account_id,
                    instance_id=instance_id,
                    error=str(exc),
                )
                raise

            history_items.append(
                InstanceAccountChangeLogItem(
                    id=cast(int, getattr(log_entry, "id", 0)),
                    change_type=cast("str | None", getattr(log_entry, "change_type", None)),
                    change_time=(time_utils.format_china_time(change_time) if change_time else "未知"),
                    status=cast("str | None", getattr(log_entry, "status", None)),
                    message=cast("str | None", getattr(log_entry, "message", None)),
                    privilege_diff=privilege_diff,
                    other_diff=other_diff,
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
