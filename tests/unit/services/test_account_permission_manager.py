from types import SimpleNamespace

import pytest

from app.errors import AppError
from app.models.account_permission import AccountPermission
from app.services.accounts_sync.permission_manager import AccountPermissionManager, SyncContext


@pytest.mark.unit
def test_apply_permissions_writes_snapshot() -> None:
    manager = AccountPermissionManager()
    record = SimpleNamespace(db_type="mysql", permission_snapshot=None)
    permissions = {"global_privileges": ["SELECT"], "unknown_field": "value"}

    manager._apply_permissions(record, permissions)

    assert isinstance(record.permission_snapshot, dict)
    assert record.permission_snapshot.get("version") == 4
    assert record.permission_snapshot.get("categories", {}).get("global_privileges") == ["SELECT"]
    assert record.permission_snapshot.get("extra", {}).get("unknown_field") == "value"
    assert isinstance(record.permission_facts, dict)
    assert record.permission_facts.get("version") == 2
    assert record.permission_facts.get("db_type") == "mysql"
    assert record.permission_facts.get("meta", {}).get("source") == "snapshot"


@pytest.mark.unit
def test_process_existing_permission_raises_when_snapshot_missing() -> None:
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
    context = SyncContext(
        instance=SimpleNamespace(id=1, name="test", db_type="mysql"), username="demo", session_id=None
    )

    with pytest.raises(AppError) as excinfo:
        manager._process_existing_permission(record, snapshot, context)

    assert excinfo.value.message_key == "SNAPSHOT_MISSING"


@pytest.mark.unit
def test_find_permission_record_raises_when_instance_account_id_missing() -> None:
    manager = AccountPermissionManager()
    record = SimpleNamespace(instance_account_id=None)

    class _Query:
        def __init__(self) -> None:
            self._last = {}

        def filter_by(self, **kwargs):  # type: ignore[no-untyped-def]
            self._last = kwargs
            return self

        def first(self):  # type: ignore[no-untyped-def]
            if "instance_account_id" in self._last:
                return None
            return record

    sentinel = object()
    original_query = AccountPermission.__dict__.get("query", sentinel)
    type.__setattr__(AccountPermission, "query", _Query())
    try:
        instance = SimpleNamespace(id=1, db_type="mysql")
        account = SimpleNamespace(id=10, username="demo")

        with pytest.raises(AppError) as excinfo:
            manager._find_permission_record(instance, account)
    finally:
        if original_query is sentinel:
            delattr(AccountPermission, "query")
        else:
            type.__setattr__(AccountPermission, "query", original_query)

    assert excinfo.value.message_key == "SYNC_DATA_ERROR"


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
