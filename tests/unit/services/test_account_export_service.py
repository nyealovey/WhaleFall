from __future__ import annotations

import csv
import io
from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.core.types.accounts_ledgers import AccountFilters, AccountLedgerMetrics
from app.services.files.account_export_service import AccountExportService


class _Repository:
    def __init__(self, account: object) -> None:
        self.account = account

    def list_all_accounts(self, _filters: AccountFilters, *, sort_field: str, sort_order: str):
        assert sort_field == "username"
        assert sort_order == "asc"
        return [self.account], AccountLedgerMetrics(tags_map={}, classifications_map={})


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
        owner_id=None,
        ad_status=None,
    )


@pytest.mark.unit
def test_account_export_csv_includes_ad_status_column() -> None:
    account = SimpleNamespace(
        id=10,
        instance_id=1,
        username="CORP\\disabled",
        is_locked=False,
        instance=SimpleNamespace(name="sql-prod", host="127.0.0.1", db_type="sqlserver"),
        instance_account=SimpleNamespace(
            ad_domain_config_id=7,
            ad_disabled_at=object(),
            ad_orphaned_at=None,
        ),
    )

    result = AccountExportService(repository=cast(Any, _Repository(account))).export_accounts_csv(_filters())
    rows = list(csv.reader(io.StringIO(result.content)))

    assert rows[0] == ["名称", "实例名称", "IP地址", "标签", "数据库类型", "分类", "锁定状态", "AD状态"]
    assert rows[1][-1] == "AD已停用"
