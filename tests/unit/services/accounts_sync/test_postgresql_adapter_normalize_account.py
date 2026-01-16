import pytest

from app.models.instance import Instance
from app.services.accounts_sync.adapters.postgresql_adapter import PostgreSQLAccountAdapter


@pytest.mark.unit
def test_normalize_account_defaults_permissions_when_missing() -> None:
    adapter = PostgreSQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="postgresql",
        host="127.0.0.1",
        port=5432,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "role1",
            "is_superuser": False,
            "is_locked": False,
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("predefined_roles") == []
    assert permissions.get("system_privileges") == []
    assert permissions.get("database_privileges_pg") == {}

    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)

    role_attributes = permissions.get("role_attributes")
    assert isinstance(role_attributes, dict)


@pytest.mark.unit
def test_normalize_account_coerces_invalid_permission_shapes() -> None:
    adapter = PostgreSQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="postgresql",
        host="127.0.0.1",
        port=5432,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "role1",
            "permissions": {
                "predefined_roles": None,
                "system_privileges": ["SUPERUSER", "", 1],
                "database_privileges_pg": {"db1": ["CONNECT", None]},
                "type_specific": [],
                "role_attributes": [],
            },
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("predefined_roles") == []
    assert permissions.get("system_privileges") == ["SUPERUSER"]
    assert permissions.get("database_privileges_pg") == {"db1": ["CONNECT"]}

    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)

    role_attributes = permissions.get("role_attributes")
    assert isinstance(role_attributes, dict)

