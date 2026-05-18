"""账户台账列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.types.accounts_ledgers import AccountFilters, AccountLedgerItem
from app.core.types.listing import PaginatedResult
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository

LOCKED_REASON_LABELS = {
    "type_specific.is_disabled=True": "账户已禁用",
    "type_specific.connect_to_engine=DENY": "CONNECT SQL 权限被拒绝",
    "type_specific.is_locked_out=True": "账户被锁定",
    "type_specific.is_password_expired=True": "密码已过期",
    "type_specific.must_change_password=True": "必须修改密码",
}


class AccountsLedgerListService:
    """账户台账列表业务编排服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        """初始化服务并注入台账仓库."""
        self._repository = repository or AccountsLedgerRepository()

    def list_accounts(
        self,
        filters: AccountFilters,
        *,
        sort_field: str,
        sort_order: str,
    ) -> PaginatedResult[AccountLedgerItem]:
        """分页列出账户台账."""
        page_result, metrics = self._repository.list_accounts(filters, sort_field=sort_field, sort_order=sort_order)
        items: list[AccountLedgerItem] = []
        for account in page_result.items:
            is_active = bool(account.instance_account.is_active)
            type_specific = account.type_specific if isinstance(account.type_specific, dict) else {}
            items.append(
                AccountLedgerItem(
                    id=account.instance_account_id,
                    username=account.username,
                    instance_name=account.instance.name,
                    instance_host=account.instance.host,
                    db_type=account.db_type,
                    is_locked=account.is_locked,
                    is_superuser=account.is_superuser,
                    is_active=is_active,
                    is_deleted=not is_active,
                    last_change_time=(account.last_change_time.isoformat() if account.last_change_time else None),
                    availability_reasons=self._build_availability_reasons(account.permission_facts),
                    type_specific=type_specific,
                    tags=metrics.tags_map.get(account.instance_id, []),
                    classifications=metrics.classifications_map.get(account.id, []),
                ),
            )
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    @staticmethod
    def _build_availability_reasons(permission_facts: object) -> list[str]:
        if not isinstance(permission_facts, dict):
            return []
        capability_reasons = permission_facts.get("capability_reasons")
        if not isinstance(capability_reasons, dict):
            return []
        locked_reasons = capability_reasons.get("LOCKED")
        if not isinstance(locked_reasons, list):
            return []

        labels: list[str] = []
        for reason in locked_reasons:
            if not isinstance(reason, str):
                continue
            label = LOCKED_REASON_LABELS.get(reason)
            if label and label not in labels:
                labels.append(label)
        return labels
