import pytest

from app.services.accounts_permissions.facts_builder import build_permission_facts


class _StubRecord:
    def __init__(self, *, db_type: str, is_superuser: bool = False, is_locked: bool = False) -> None:
        self.db_type = db_type
        self.is_superuser = is_superuser
        self.is_locked = is_locked


@pytest.mark.unit
def test_build_permission_facts_sqlserver_includes_database_roles_in_roles() -> None:
    record = _StubRecord(db_type="sqlserver")
    permissions = {
        "server_roles": [{"name": "sysadmin"}],
        "database_roles": {"db1": [{"name": "db_owner"}]},
        "server_permissions": ["CONTROL SERVER"],
        "database_permissions": {"db1": ["ALTER"]},
    }
    facts = build_permission_facts(record=record, permissions=permissions, snapshot=None)
    assert set(facts["roles"]) == {"sysadmin", "db_owner"}


@pytest.mark.unit
def test_build_permission_facts_postgresql_maps_role_attributes_to_capabilities() -> None:
    record = _StubRecord(db_type="postgresql", is_superuser=False)
    permissions = {"role_attributes": {"can_super": True, "can_create_role": True, "can_create_db": True}}
    facts = build_permission_facts(record=record, permissions=permissions, snapshot=None)

    assert "can_super" in facts["capabilities"]
    assert "can_create_role" in facts["capabilities"]
    assert "can_create_db" in facts["capabilities"]
    assert "GRANT_ADMIN" in facts["capabilities"]
