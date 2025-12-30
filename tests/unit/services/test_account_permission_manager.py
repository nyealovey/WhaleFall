from types import SimpleNamespace

import pytest

from app.services.accounts_sync.permission_manager import AccountPermissionManager


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


@pytest.mark.unit
def test_apply_permissions_does_not_write_snapshot_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("ACCOUNT_PERMISSION_SNAPSHOT_WRITE", raising=False)
    manager = AccountPermissionManager()
    record = SimpleNamespace(db_type="mysql", permission_snapshot=None)
    permissions = {"global_privileges": ["SELECT"]}

    manager._apply_permissions(record, permissions, is_superuser=False, is_locked=False)

    assert record.permission_snapshot is None
