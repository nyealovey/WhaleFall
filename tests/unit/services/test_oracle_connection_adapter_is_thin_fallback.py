import pytest

from app.services.connection_adapters.adapters import oracle_adapter


class _StubCredential:
    username = "scott"

    @staticmethod
    def get_plain_password() -> str:
        return "secret"


class _StubInstance:
    id = 1
    host = "127.0.0.1"
    port = 1521
    database_name = None
    credential = _StubCredential()


@pytest.mark.unit
def test_oracle_connection_is_thin_probe_failure_logs_fallback(monkeypatch) -> None:
    connection = oracle_adapter.OracleConnection(_StubInstance())  # type: ignore[arg-type]

    calls: list[tuple[str, str, dict[str, object]]] = []

    def _log_fallback(level: str, event: str, **kwargs: object) -> None:
        calls.append((level, event, dict(kwargs)))

    def _raise_is_thin() -> bool:
        raise RuntimeError("boom")

    def _raise_connect(**_: object) -> object:
        raise ConnectionError("nope")

    monkeypatch.setattr(oracle_adapter, "log_fallback", _log_fallback)
    monkeypatch.setattr(oracle_adapter.oracledb, "is_thin", _raise_is_thin, raising=False)
    monkeypatch.setattr(oracle_adapter.oracledb, "init_oracle_client", lambda **_: None)
    monkeypatch.setattr(oracle_adapter.oracledb, "connect", _raise_connect)

    assert connection.connect() is False
    assert calls

    level, event, payload = calls[0]
    assert level == "warning"
    assert event == "oracle_is_thin_check_failed_fallback"
    assert payload.get("fallback_reason") == "oracledb_is_thin_check_failed"
    assert isinstance(payload.get("exception"), RuntimeError)
