from types import SimpleNamespace
from typing import Any

import oracledb  # type: ignore[import-not-found]
import pytest

from app.services.database_sync.table_size_adapters.oracle_adapter import OracleTableSizeAdapter


class _DummyOracleConnection:
    def __init__(self, handler):  # noqa: ANN001
        self._handler = handler

    def execute_query(self, query, params=None):  # noqa: ANN001
        return self._handler(query, params)


def _oracle_error(code: str) -> Exception:
    return oracledb.DatabaseError(f"{code}: 表或视图不存在")


@pytest.mark.unit
def test_oracle_table_size_adapter_fallback_to_all_segments() -> None:
    adapter = OracleTableSizeAdapter()
    instance: Any = SimpleNamespace(name="instance-1", credential=SimpleNamespace(username="app_user"))

    def handler(query: str, params):  # noqa: ANN001
        del params
        normalized = " ".join(query.lower().split())
        if "from dba_tablespaces" in normalized:
            raise _oracle_error("ORA-00942")
        if "from user_tablespaces" in normalized:
            raise _oracle_error("ORA-00942")
        if "from dba_segments" in normalized:
            raise _oracle_error("ORA-00942")
        if "from all_segments" in normalized:
            return [
                ("APP", "USERS", 12),
                ("APP", "ORDERS", 5),
            ]
        raise AssertionError(f"unexpected query: {normalized}")

    connection: Any = _DummyOracleConnection(handler)
    tables = adapter.fetch_table_sizes(instance, connection, "USERS")
    assert isinstance(tables, list)
    assert len(tables) == 2
    assert tables[0]["schema_name"] == "APP"
    assert tables[0]["table_name"] == "USERS"
    assert tables[0]["size_mb"] == 12


@pytest.mark.unit
def test_oracle_table_size_adapter_missing_privileges_raises_value_error() -> None:
    adapter = OracleTableSizeAdapter()
    instance: Any = SimpleNamespace(name="instance-1", credential=SimpleNamespace(username="app_user"))

    def handler(query: str, params):  # noqa: ANN001
        del query, params
        raise _oracle_error("ORA-00942")

    with pytest.raises(ValueError, match="权限"):
        connection: Any = _DummyOracleConnection(handler)
        adapter.fetch_table_sizes(instance, connection, "USERS")


@pytest.mark.unit
def test_oracle_table_size_adapter_empty_result_without_tablespace_check_raises_value_error() -> None:
    adapter = OracleTableSizeAdapter()
    instance: Any = SimpleNamespace(name="instance-1", credential=SimpleNamespace(username="app_user"))

    def handler(query: str, params):  # noqa: ANN001
        del params
        normalized = " ".join(query.lower().split())
        if "from dba_tablespaces" in normalized:
            raise _oracle_error("ORA-00942")
        if "from user_tablespaces" in normalized:
            raise _oracle_error("ORA-00942")
        if "from dba_segments" in normalized:
            raise _oracle_error("ORA-00942")
        if "from all_segments" in normalized:
            return []
        raise AssertionError(f"unexpected query: {normalized}")

    with pytest.raises(ValueError, match="未采集到任何表容量数据"):
        connection: Any = _DummyOracleConnection(handler)
        adapter.fetch_table_sizes(instance, connection, "USERS")
