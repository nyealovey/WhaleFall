from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.types.accounts_ledgers import AccountFilters, AccountLedgerMetrics
from app.core.types.listing import PaginatedResult
from app.services.ledgers.accounts_ledger_list_service import AccountsLedgerListService


class _Repository:
    def __init__(self, account: object) -> None:
        self.account = account

    def list_accounts(self, _filters: AccountFilters, *, sort_field: str, sort_order: str):
        assert sort_field == "username"
        assert sort_order == "asc"
        return (
            PaginatedResult(items=[self.account], total=1, page=1, pages=1, limit=20),
            AccountLedgerMetrics(tags_map={}, classifications_map={}),
        )


def _filters() -> AccountFilters:
    return AccountFilters(
        page=1,
        limit=20,
        search="",
        instance_id=None,
        include_deleted=False,
        include_roles=False,
        is_locked=None,
        is_superuser=None,
        plugin="",
        tags=[],
        classification="",
        classification_filter="",
        db_type=None,
        owner_type=None,
        ad_status=None,
    )


@pytest.mark.unit
def test_accounts_ledger_list_service_serializes_ad_status_fields() -> None:
    account = SimpleNamespace(
        id=10,
        instance_account_id=100,
        username="CORP\\disabled",
        instance=SimpleNamespace(name="sql-prod", host="127.0.0.1"),
        instance_id=1,
        db_type="sqlserver",
        is_locked=False,
        is_superuser=False,
        last_change_time=None,
        type_specific={},
        permission_facts={},
        owner_type="instance",
        availability_group_id=None,
        instance_account=SimpleNamespace(
            is_active=True,
            availability_group_id=None,
            ad_domain_config_id=7,
            ad_disabled_at=SimpleNamespace(isoformat=lambda: "2026-05-21T01:30:00+08:00"),
            ad_orphaned_at=None,
            ad_domain_config=SimpleNamespace(netbios_name="CORP"),
        ),
    )

    result = AccountsLedgerListService(repository=cast(Any, _Repository(account))).list_accounts(
        _filters(),
        sort_field="username",
        sort_order="asc",
    )

    item = result.items[0]
    assert item.ad_status == "disabled"
    assert item.ad_domain == "CORP"
    assert item.ad_disabled_at == "2026-05-21T01:30:00+08:00"
    assert item.ad_orphaned_at is None
