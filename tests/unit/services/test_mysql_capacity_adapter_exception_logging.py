from __future__ import annotations

from typing import Any, cast

import pytest

from app.services.database_sync.adapters.mysql_adapter import MySQLCapacityAdapter


class _DummyLogger:
    def __init__(self) -> None:
        self.exception_calls: list[tuple[str, dict[str, object]]] = []

    def exception(self, event: str, **kwargs: object) -> None:
        self.exception_calls.append((event, dict(kwargs)))


class _DummyInstance:
    def __init__(self, name: str) -> None:
        self.name = name


@pytest.mark.unit
def test_mysql_fetch_capacity_logs_and_reraises_when_tablespace_collection_fails(monkeypatch) -> None:
    adapter = MySQLCapacityAdapter()
    logger = _DummyLogger()
    cast(Any, adapter).logger = logger

    def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(adapter, "_assert_permission", _noop)
    monkeypatch.setattr(adapter, "_collect_tablespace_sizes", _boom)

    instance = cast(Any, _DummyInstance("inst-1"))
    connection = cast(Any, object())

    with pytest.raises(RuntimeError):
        adapter.fetch_capacity(instance, connection, target_databases=["db1"])

    assert len(logger.exception_calls) == 1
    event, kwargs = logger.exception_calls[0]
    assert event == "mysql_tablespace_collection_failed"
    assert kwargs["instance"] == "inst-1"
    assert kwargs["error"] == "boom"
