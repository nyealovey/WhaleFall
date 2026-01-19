"""账户台账列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.types.accounts_ledgers import AccountFilters, AccountLedgerItem
from app.core.types.listing import PaginatedResult
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository


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
