from types import SimpleNamespace

import pytest

from app.services.accounts_sync.permission_manager import AccountPermissionManager, SyncContext


@pytest.mark.unit
def test_apply_permissions_writes_snapshot() -> None:
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
def test_process_existing_permission_backfills_snapshot_when_missing() -> None:
    manager = AccountPermissionManager()

    record = SimpleNamespace(
        db_type="mysql",
        is_superuser=False,
        is_locked=False,
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


@pytest.mark.unit
def test_calculate_diff_uses_snapshot_view_not_legacy_columns() -> None:
    manager = AccountPermissionManager()
    record = SimpleNamespace(
        db_type="mysql",
        permission_snapshot={
            "version": 4,
            "categories": {
                "global_privileges": ["SELECT"],
            },
            "type_specific": {"mysql": {"host": "%"}},
            "extra": {},
            "errors": [],
            "meta": {},
        },
        is_superuser=False,
        is_locked=False,
    )

    diff = manager._calculate_diff(
        record,
        {"global_privileges": ["SELECT", "INSERT"], "type_specific": {"host": "localhost"}},
        is_superuser=False,
        is_locked=False,
    )

    assert diff.get("changed") is True
    assert diff.get("change_type") == "modify_privilege"
    privilege_diff = diff.get("privilege_diff")
    assert isinstance(privilege_diff, list)
    assert any(
        entry.get("action") == "GRANT" and "INSERT" in (entry.get("permissions") or []) for entry in privilege_diff
    )
    other_diff = diff.get("other_diff")
    assert isinstance(other_diff, list)
    assert any(entry.get("field") == "type_specific" for entry in other_diff)
