"""账户台账列表 Service.

职责:
- 组织 repository 调用并将 ORM 对象转换为稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.types.accounts_ledgers import AccountFilters, AccountLedgerItem
from app.types.listing import PaginatedResult


class AccountsLedgerListService:
    """账户台账列表业务编排服务."""

    def __init__(self, repository: AccountsLedgerRepository | None = None) -> None:
        self._repository = repository or AccountsLedgerRepository()

    def list_accounts(
        self,
        filters: AccountFilters,
        *,
        sort_field: str,
        sort_order: str,
    ) -> PaginatedResult[AccountLedgerItem]:
        page_result, metrics = self._repository.list_accounts(filters, sort_field=sort_field, sort_order=sort_order)
        items: list[AccountLedgerItem] = []
        for account in page_result.items:
            instance = account.instance
            instance_account = account.instance_account
            is_active = bool(instance_account.is_active) if instance_account else True
            items.append(
                AccountLedgerItem(
                    id=account.id,
                    username=account.username,
                    instance_name=instance.name if instance else "未知实例",
                    instance_host=instance.host if instance else "未知主机",
                    db_type=account.db_type,
                    is_locked=bool(account.is_locked),
                    is_superuser=bool(account.is_superuser),
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

