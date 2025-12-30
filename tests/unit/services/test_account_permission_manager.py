from types import SimpleNamespace

import pytest

from app.services.accounts_sync.permission_manager import AccountPermissionManager, SyncContext


@pytest.mark.unit
def test_apply_permissions_writes_snapshot_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("ACCOUNT_PERMISSION_SNAPSHOT_WRITE", "true")
    manager = AccountPermissionManager()
    record = SimpleNamespace(db_type="mysql", permission_snapshot=None)
    permissions = {"global_privileges": ["SELECT"], "unknown_field": "value"}

    manager._apply_permissions(record, permissions, is_superuser=False, is_locked=False)

    assert isinstance(record.permission_snapshot, dict)
    assert record.permission_snapshot.get("version") == 4
    assert record.permission_snapshot.get("categories", {}).get("global_privileges") == ["SELECT"]
    assert record.permission_snapshot.get("extra", {}).get("unknown_field") == "value"
    assert isinstance(record.permission_facts, dict)
    assert record.permission_facts.get("version") == 1
    assert record.permission_facts.get("db_type") == "mysql"
    assert record.permission_facts.get("meta", {}).get("source") == "snapshot"


@pytest.mark.unit
def test_apply_permissions_does_not_write_snapshot_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("ACCOUNT_PERMISSION_SNAPSHOT_WRITE", raising=False)
    manager = AccountPermissionManager()
    record = SimpleNamespace(db_type="mysql", permission_snapshot=None)
    permissions = {"global_privileges": ["SELECT"]}

    manager._apply_permissions(record, permissions, is_superuser=False, is_locked=False)

    assert record.permission_snapshot is None
    assert isinstance(record.permission_facts, dict)
    assert record.permission_facts.get("db_type") == "mysql"
    assert record.permission_facts.get("meta", {}).get("source") == "legacy"


@pytest.mark.unit
def test_process_existing_permission_backfills_snapshot_when_missing(monkeypatch) -> None:
    monkeypatch.setenv("ACCOUNT_PERMISSION_SNAPSHOT_WRITE", "true")
    manager = AccountPermissionManager()

    record = SimpleNamespace(
        db_type="mysql",
        is_superuser=False,
        is_locked=False,
        global_privileges=["SELECT"],
        database_privileges={"db1": ["SELECT"]},
        predefined_roles=None,
        role_attributes=None,
        database_privileges_pg=None,
        tablespace_privileges=None,
        server_roles=None,
        server_permissions=None,
        database_roles=None,
        database_permissions=None,
        oracle_roles=None,
        system_privileges=None,
        tablespace_privileges_oracle=None,
        type_specific=None,
        permission_snapshot=None,
        last_sync_time=None,
    )

    remote = {
        "permissions": {"global_privileges": ["SELECT"], "database_privileges": {"db1": ["SELECT"]}},
        "is_superuser": False,
        "is_locked": False,
    }
    snapshot = manager._extract_remote_context(remote)
    context = SyncContext(instance=SimpleNamespace(id=1, name="test", db_type="mysql"), username="demo", session_id=None)

    outcome = manager._process_existing_permission(record, snapshot, context)

    assert outcome.updated == 1
    assert isinstance(record.permission_snapshot, dict)
    assert record.permission_snapshot.get("version") == 4
    assert isinstance(record.permission_facts, dict)
    assert record.permission_facts.get("meta", {}).get("source") == "snapshot"
