from types import SimpleNamespace
from typing import cast

import pytest

from app.core.exceptions import AppError
from app.repositories.instance_accounts_repository import InstanceAccountsRepository
from app.repositories.ledgers.accounts_ledger_repository import AccountsLedgerRepository
from app.services.instances.instance_accounts_service import InstanceAccountsService
from app.services.ledgers.accounts_ledger_permissions_service import AccountsLedgerPermissionsService


class _StubLedgerRepository:
    def __init__(self, account):
        self._account = account

    def get_account_by_instance_account_id(self, instance_account_id: int):
        del instance_account_id
        return self._account


class _StubInstanceAccountsRepository:
    def __init__(self, instance, account):
        self._instance = instance
        self._account = account

    def get_instance(self, instance_id: int):
        return self._instance

    def get_account(self, *, instance_id: int, account_id: int):
        return self._account


@pytest.mark.unit
def test_accounts_ledger_permissions_snapshot_missing_raises() -> None:
    instance = SimpleNamespace(db_type="mysql", name="instance-1")
    account = SimpleNamespace(
        id=1,
        instance_account_id=1,
        instance_id=1,
        instance=instance,
        username="demo",
        is_superuser=False,
        last_sync_time=None,
        permission_snapshot=None,
    )

    service = AccountsLedgerPermissionsService(
        repository=cast(AccountsLedgerRepository, _StubLedgerRepository(account)),
    )
    with pytest.raises(AppError) as exc:
        service.get_permissions(1)

    assert exc.value.message_key == "SNAPSHOT_MISSING"


@pytest.mark.unit
def test_accounts_ledger_permissions_snapshot_present_prefers_snapshot() -> None:
    instance = SimpleNamespace(db_type="mysql", name="instance-1")
    account = SimpleNamespace(
        id=1,
        instance_account_id=1,
        instance_id=1,
        instance=instance,
        username="demo",
        is_superuser=False,
        last_sync_time=None,
        permission_snapshot={
            "version": 4,
            "categories": {
                "mysql_global_privileges": ["SELECT"],
                "mysql_database_privileges": {"db1": ["CREATE"]},
            },
            "type_specific": {},
            "extra": {},
            "errors": [],
            "meta": {},
        },
    )

    service = AccountsLedgerPermissionsService(
        repository=cast(AccountsLedgerRepository, _StubLedgerRepository(account)),
    )
    result = service.get_permissions(1)
    assert result.permissions.snapshot.get("version") == 4
    assert result.permissions.snapshot.get("categories", {}).get("mysql_global_privileges") == ["SELECT"]
    assert result.permissions.snapshot.get("categories", {}).get("mysql_database_privileges") == {"db1": ["CREATE"]}


@pytest.mark.unit
def test_instance_account_permissions_snapshot_missing_raises() -> None:
    instance = SimpleNamespace(db_type="mysql", name="instance-1")
    account = SimpleNamespace(
        id=1,
        username="demo",
        is_superuser=False,
        last_sync_time=None,
        permission_snapshot=None,
    )

    service = InstanceAccountsService(
        repository=cast(
            InstanceAccountsRepository,
            _StubInstanceAccountsRepository(instance, account),
        ),
    )
    with pytest.raises(AppError) as exc:
        service.get_account_permissions(1, 1)

    assert exc.value.message_key == "SNAPSHOT_MISSING"
