import pytest

from app.models.instance import Instance
from app.services.accounts_sync.adapters.mysql_adapter import MySQLAccountAdapter


@pytest.mark.unit
def test_normalize_account_defaults_permissions_when_missing() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "user@localhost",
            "is_superuser": False,
            "is_locked": False,
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("global_privileges") == []
    assert permissions.get("database_privileges") == {}
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("original_username") == "user"
    assert type_specific.get("host") == "localhost"


@pytest.mark.unit
def test_normalize_account_accepts_empty_permissions_dict() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "user@localhost",
            "permissions": {},
        },
    )

    permissions = normalized["permissions"]
    assert permissions.get("global_privileges") == []
    assert permissions.get("database_privileges") == {}
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("original_username") == "user"
    assert type_specific.get("host") == "localhost"


@pytest.mark.unit
def test_normalize_account_coerces_invalid_type_specific_to_dict() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "user@localhost",
            "permissions": {"type_specific": []},
        },
    )

    permissions = normalized["permissions"]
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("original_username") == "user"
    assert type_specific.get("host") == "localhost"


@pytest.mark.unit
def test_normalize_account_does_not_override_existing_type_specific_identity() -> None:
    adapter = MySQLAccountAdapter()
    instance = Instance(
        name="inst",
        db_type="mysql",
        host="127.0.0.1",
        port=3306,
        description=None,
        is_active=True,
    )

    normalized = adapter._normalize_account(
        instance,
        {
            "username": "user@localhost",
            "permissions": {"type_specific": {"original_username": "custom", "host": "remote"}},
        },
    )

    permissions = normalized["permissions"]
    type_specific = permissions.get("type_specific")
    assert isinstance(type_specific, dict)
    assert type_specific.get("original_username") == "custom"
    assert type_specific.get("host") == "remote"
