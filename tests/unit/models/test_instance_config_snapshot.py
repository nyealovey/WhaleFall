import pytest
from sqlalchemy.dialects import postgresql

from app import db


@pytest.mark.unit
def test_instance_config_snapshot_table_contract_has_expected_constraints() -> None:
    table = db.metadata.tables["instance_config_snapshots"]

    column_names = set(table.c.keys())
    assert {
        "instance_id",
        "db_type",
        "config_key",
        "snapshot",
        "facts",
        "last_sync_time",
    }.issubset(column_names)

    index_names = {index.name for index in table.indexes if index.name}
    assert "ix_instance_config_snapshots_instance_config_key" in index_names
    assert "ix_instance_config_snapshots_config_key" in index_names
    assert "ix_instance_config_snapshots_last_sync_time" in index_names

    constraint_names = {constraint.name for constraint in table.constraints if constraint.name}
    assert "uq_instance_config_snapshot_instance_config_key" in constraint_names


@pytest.mark.unit
def test_instance_config_snapshot_json_columns_contract() -> None:
    table = db.metadata.tables["instance_config_snapshots"]
    snapshot_column = table.c["snapshot"]
    facts_column = table.c["facts"]

    assert snapshot_column.nullable is True
    assert facts_column.nullable is True
    assert isinstance(snapshot_column.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)
    assert isinstance(facts_column.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)
