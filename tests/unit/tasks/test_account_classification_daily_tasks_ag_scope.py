from types import SimpleNamespace

import pytest

from app.tasks import account_classification_daily_tasks as daily_tasks


@pytest.mark.unit
def test_daily_account_indexes_keep_ag_accounts_as_separate_owner_scope() -> None:
    physical_account = SimpleNamespace(
        id=1,
        db_type="sqlserver",
        instance_id=10,
        owner_type="instance",
        owner_id=10,
    )
    ag_account = SimpleNamespace(
        id=2,
        db_type="sqlserver",
        instance_id=10,
        owner_type="sqlserver_ag",
        owner_id=42,
    )

    accounts_by_db_type, owner_scopes_by_db_type = daily_tasks._build_account_indexes(
        [physical_account, ag_account],
    )

    assert accounts_by_db_type["sqlserver"] == [physical_account, ag_account]
    assert owner_scopes_by_db_type["sqlserver"] == {
        ("instance", 10, 10),
        ("sqlserver_ag", 42, 10),
    }
