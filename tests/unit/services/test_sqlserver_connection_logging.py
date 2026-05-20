from types import SimpleNamespace

import pytest

from app.services.connection_adapters.adapters import sqlserver_adapter
from app.services.connection_adapters.adapters.sqlserver_adapter import SQLServerConnection


@pytest.mark.unit
def test_sqlserver_connection_failure_log_keeps_database_target_host(monkeypatch) -> None:
    instance = SimpleNamespace(
        id=71,
        host="AGDB10.wz.dc",
        port=1433,
        database_name="master",
        credential=SimpleNamespace(username="jt_mssqlinfo_srv", get_plain_password=lambda: "secret"),
    )
    connection = SQLServerConnection(instance)
    logged: dict[str, object] = {}

    class _FakeLogger:
        def exception(self, event: str, **kwargs) -> None:
            logged["event"] = event
            logged.update(kwargs)

    def _raise_connect_error(*args, **kwargs):
        _ = (args, kwargs)
        raise RuntimeError("18456 登录失败")

    connection.db_logger = _FakeLogger()
    monkeypatch.setattr(sqlserver_adapter.pymssql, "connect", _raise_connect_error)

    assert connection.connect() is False
    assert logged["event"] == "SQL Server连接失败"
    assert logged["target_host"] == "AGDB10.wz.dc"
    assert logged["target_port"] == 1433
    assert logged["target_database"] == "master"
    assert logged["username"] == "jt_mssqlinfo_srv"
