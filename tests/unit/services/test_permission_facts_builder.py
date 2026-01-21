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
    snapshot = {
        "version": 4,
        "categories": {
            "sqlserver_server_roles": [{"name": "sysadmin"}],
            "sqlserver_database_roles": {"db1": [{"name": "db_owner"}]},
            "sqlserver_server_permissions": ["CONTROL SERVER"],
            "sqlserver_database_permissions": {"db1": ["ALTER"]},
        },
        "type_specific": {},
        "extra": {},
        "errors": [],
        "meta": {},
    }
    facts = build_permission_facts(record=record, snapshot=snapshot)
    assert set(facts["roles"]) == {"sysadmin", "db_owner"}


@pytest.mark.unit
def test_build_permission_facts_sqlserver_does_not_treat_is_disabled_as_locked() -> None:
    record = _StubRecord(db_type="sqlserver")
    snapshot = {
        "version": 4,
        "categories": {},
        "type_specific": {"sqlserver": {"is_disabled": True}},
        "extra": {},
        "errors": [],
        "meta": {},
    }
    facts = build_permission_facts(record=record, snapshot=snapshot)
    assert "LOCKED" not in facts["capabilities"]


@pytest.mark.unit
def test_build_permission_facts_sqlserver_adds_locked_for_connect_denied() -> None:
    record = _StubRecord(db_type="sqlserver")
    snapshot = {
        "version": 4,
        "categories": {},
        "type_specific": {"sqlserver": {"connect_to_engine": "DENY"}},
        "extra": {},
        "errors": [],
        "meta": {},
    }
    facts = build_permission_facts(record=record, snapshot=snapshot)
    assert "LOCKED" in facts["capabilities"]


@pytest.mark.unit
def test_build_permission_facts_postgresql_maps_role_attributes_to_capabilities() -> None:
    record = _StubRecord(db_type="postgresql", is_superuser=False)
    snapshot = {
        "version": 4,
        "categories": {
            "postgresql_role_attributes": {"can_super": True, "can_create_role": True, "can_create_db": True},
        },
        "type_specific": {},
        "extra": {},
        "errors": [],
        "meta": {},
    }
    facts = build_permission_facts(record=record, snapshot=snapshot)

    assert "can_super" in facts["capabilities"]
    assert "can_create_role" in facts["capabilities"]
    assert "can_create_db" in facts["capabilities"]
    assert "GRANT_ADMIN" in facts["capabilities"]


@pytest.mark.unit
def test_build_permission_facts_includes_internal_contract_error_in_meta() -> None:
    record = _StubRecord(db_type="sqlserver")
    facts = build_permission_facts(record=record, snapshot={"version": 3, "categories": {}})
    meta = facts.get("meta", {})
    assert isinstance(meta, dict)
    assert meta.get("snapshot_contract_ok") is False
    assert meta.get("snapshot_error_code") == "INTERNAL_CONTRACT_UNKNOWN_VERSION"
    assert meta.get("type_specific_contract_ok") is False
    assert meta.get("type_specific_error_code") == "INTERNAL_CONTRACT_UNKNOWN_VERSION"
    assert "INTERNAL_CONTRACT_UNKNOWN_VERSION" in facts.get("errors", [])


@pytest.mark.unit
def test_build_permission_facts_includes_internal_contract_error_when_version_is_not_int() -> None:
    record = _StubRecord(db_type="sqlserver")
    facts = build_permission_facts(record=record, snapshot={"version": "4", "categories": {}, "type_specific": {}})
    meta = facts.get("meta", {})
    assert isinstance(meta, dict)
    assert meta.get("snapshot_contract_ok") is False
    assert meta.get("snapshot_error_code") == "INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS"
    assert meta.get("type_specific_contract_ok") is False
    assert meta.get("type_specific_error_code") == "INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS"
    assert "INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS" in facts.get("errors", [])


@pytest.mark.unit
def test_build_permission_facts_includes_type_specific_contract_error_when_shape_invalid() -> None:
    record = _StubRecord(db_type="sqlserver")
    facts = build_permission_facts(record=record, snapshot={"version": 4, "categories": {}, "type_specific": None})
    meta = facts.get("meta", {})
    assert isinstance(meta, dict)
    assert meta.get("snapshot_contract_ok") is True
    assert meta.get("type_specific_contract_ok") is False
    assert meta.get("type_specific_error_code") == "INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS"
    assert "INTERNAL_CONTRACT_MISSING_REQUIRED_FIELDS" in facts.get("errors", [])


@pytest.mark.unit
def test_build_permission_facts_mysql_roles_include_direct_and_default() -> None:
    record = _StubRecord(db_type="mysql")
    snapshot = {
        "version": 4,
        "categories": {"mysql_granted_roles": {"direct": ["r1@%"], "default": ["r2@%"]}},
        "type_specific": {"mysql": {"account_kind": "user"}},
        "extra": {},
        "errors": [],
        "meta": {},
    }

    facts = build_permission_facts(record=record, snapshot=snapshot)

    assert set(facts["roles"]) == {"r1@%", "r2@%"}


@pytest.mark.unit
def test_build_permission_facts_mysql_role_does_not_add_locked() -> None:
    record = _StubRecord(db_type="mysql")
    snapshot = {
        "version": 4,
        "categories": {},
        "type_specific": {"mysql": {"account_kind": "role", "account_locked": True}},
        "extra": {},
        "errors": [],
        "meta": {},
    }

    facts = build_permission_facts(record=record, snapshot=snapshot)

    assert "LOCKED" not in facts["capabilities"]
