import pytest

from app.models.instance import Instance
from app.services.accounts_sync.adapters.oracle_adapter import OracleAccountAdapter


@pytest.mark.unit
def test_normalize_account_defaults_permissions_when_missing() -> None:
    adapter = OracleAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="oracle",
        host="127.0.0.1",
        port=1521,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "USER1",
            "is_superuser": False,
            "is_locked": False,
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("oracle_roles") == []
    assert permissions.get("oracle_system_privileges") == []
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)


@pytest.mark.unit
def test_normalize_account_coerces_invalid_permission_shapes() -> None:
    adapter = OracleAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="oracle",
        host="127.0.0.1",
        port=1521,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "USER1",
            "permissions": {
                "oracle_roles": ["DBA", "", 1],
                "oracle_system_privileges": ["GRANT ANY PRIVILEGE", None],
                "type_specific": [],
            },
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("oracle_roles") == ["DBA"]
    assert permissions.get("oracle_system_privileges") == ["GRANT ANY PRIVILEGE"]
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
