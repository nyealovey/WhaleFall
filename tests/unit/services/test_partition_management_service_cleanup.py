from contextlib import contextmanager
from datetime import date

import pytest

from app import db
from app.services.partition_management_service import PartitionManagementService


@pytest.mark.unit
def test_partition_management_service_does_not_expose_create_future_partitions() -> None:
    assert not hasattr(PartitionManagementService, "create_future_partitions")


@pytest.mark.unit
def test_create_partition_does_not_create_partition_indexes(monkeypatch) -> None:
    service = PartitionManagementService()
    monkeypatch.setattr(service, "_partition_exists", lambda _name: False)

    executed_sql: list[str] = []

    def _execute(statement, _params=None):
        executed_sql.append(str(statement))
        return None

    @contextmanager
    def _begin_nested():
        yield

    monkeypatch.setattr(db.session, "execute", _execute)
    monkeypatch.setattr(db.session, "begin_nested", _begin_nested)
    monkeypatch.setattr(db.session, "flush", lambda: None)

    service.create_partition(date(2099, 12, 27))

    assert any("CREATE TABLE" in sql.upper() for sql in executed_sql)
    assert any("COMMENT ON TABLE" in sql.upper() for sql in executed_sql)
    assert not any("CREATE INDEX" in sql.upper() for sql in executed_sql)
