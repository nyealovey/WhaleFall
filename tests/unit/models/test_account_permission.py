import pytest

from app import db
from app.models.account_permission import AccountPermission  # noqa: F401
from sqlalchemy import cast, func, select
from sqlalchemy.dialects import postgresql


@pytest.mark.unit
def test_account_permission_table_contract_has_expected_constraints() -> None:
    table = db.metadata.tables["account_permission"]

    column_names = set(table.c.keys())
    assert {"instance_id", "db_type", "username", "permission_snapshot", "permission_facts"}.issubset(column_names)

    index_names = {index.name for index in table.indexes if index.name}
    assert "idx_account_permission_instance_dbtype" in index_names
    assert "idx_account_permission_username" in index_names

    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    assert "uq_account_permission" in constraint_names


@pytest.mark.unit
def test_account_permission_snapshot_columns_contract() -> None:
    """Phase 0 contract test: skip until snapshot columns land."""

    table = db.metadata.tables["account_permission"]
    if "permission_snapshot" not in table.c or "permission_facts" not in table.c:
        pytest.skip("permission_snapshot columns not implemented yet")

    snapshot_column = table.c["permission_snapshot"]
    assert snapshot_column.nullable is True
    assert isinstance(snapshot_column.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)

    facts_column = table.c["permission_facts"]
    assert facts_column.nullable is True
    assert isinstance(facts_column.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)


@pytest.mark.unit
def test_account_permission_capability_expression_uses_jsonb_contains_operator() -> None:
    table = db.metadata.tables["account_permission"]
    capabilities = cast(table.c.permission_facts["capabilities"], postgresql.JSONB)
    stmt = select(table.c.id).where(func.coalesce(capabilities.contains(["SUPERUSER"]), False).is_(True))
    compiled = str(stmt.compile(dialect=postgresql.dialect()))
    assert "LIKE" not in compiled
    assert "@>" in compiled
