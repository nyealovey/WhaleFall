import pytest

from app.models.instance import Instance
from app.services.accounts_sync.adapters.sqlserver_adapter import SQLServerAccountAdapter


@pytest.mark.unit
def test_normalize_account_defaults_permissions_when_missing() -> None:
    adapter = SQLServerAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="sqlserver",
        host="127.0.0.1",
        port=1433,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "login1",
            "is_superuser": False,
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("server_roles") == []
    assert permissions.get("server_permissions") == []
    assert permissions.get("database_roles") == {}
    assert permissions.get("database_permissions") == {}

    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("is_disabled") is False
