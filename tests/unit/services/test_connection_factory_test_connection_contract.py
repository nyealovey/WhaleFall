import pytest

from app.services.connection_adapters.adapters.mysql_adapter import MySQLConnection
from app.services.connection_adapters.adapters.oracle_adapter import OracleConnection
from app.services.connection_adapters.adapters.postgresql_adapter import PostgreSQLConnection
from app.services.connection_adapters.adapters.sqlserver_adapter import SQLServerConnection


class _StubInstance:
    id = 1
    host = "127.0.0.1"
    port = 1234
    database_name = None
    credential = None


@pytest.mark.unit
def test_adapter_test_connection_connect_failure_includes_message(monkeypatch) -> None:
    for connection_cls in [MySQLConnection, PostgreSQLConnection, SQLServerConnection, OracleConnection]:
        connection = connection_cls(_StubInstance())
        monkeypatch.setattr(connection, "connect", lambda: False)
        monkeypatch.setattr(connection, "disconnect", lambda: None)

        result = connection.test_connection()

        assert result["success"] is False
        assert isinstance(result.get("message"), str)
        assert result["message"]


@pytest.mark.unit
def test_adapter_test_connection_exception_includes_message(monkeypatch) -> None:
    for connection_cls in [MySQLConnection, PostgreSQLConnection, SQLServerConnection, OracleConnection]:
        connection = connection_cls(_StubInstance())

        def _raise() -> bool:
            raise RuntimeError("boom")

        monkeypatch.setattr(connection, "connect", _raise)
        monkeypatch.setattr(connection, "disconnect", lambda: None)

        result = connection.test_connection()

        assert result["success"] is False
        assert isinstance(result.get("message"), str)
        assert result["message"]
        assert isinstance(result.get("error"), str)
        assert result["error"]
