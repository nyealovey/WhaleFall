import pytest

from app import db
from app.models.account_permission import AccountPermission  # noqa: F401
from sqlalchemy.dialects import postgresql


@pytest.mark.unit
def test_account_permission_table_contract_has_expected_constraints() -> None:
    table = db.metadata.tables["account_permission"]

    column_names = set(table.c.keys())
    assert {"instance_id", "db_type", "username", "is_superuser", "is_locked"}.issubset(column_names)

    index_names = {index.name for index in table.indexes if index.name}
    assert "idx_account_permission_instance_dbtype" in index_names
    assert "idx_account_permission_username" in index_names

    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    assert "uq_account_permission" in constraint_names


@pytest.mark.unit
def test_account_permission_snapshot_columns_contract() -> None:
    """Phase 0 contract test: skip until snapshot columns land."""

    table = db.metadata.tables["account_permission"]
    if "permission_snapshot" not in table.c or "permission_snapshot_version" not in table.c:
        pytest.skip("permission_snapshot columns not implemented yet")

    snapshot_column = table.c["permission_snapshot"]
    assert snapshot_column.nullable is True
    assert isinstance(snapshot_column.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)

    version_column = table.c["permission_snapshot_version"]
    assert version_column.nullable is False

    if version_column.default is not None:
        assert getattr(version_column.default, "arg", None) == 4
