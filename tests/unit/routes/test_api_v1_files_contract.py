import pytest

from app.services.ledgers.database_ledger_service import DatabaseLedgerService


@pytest.mark.unit
def test_api_v1_files_requires_auth(client) -> None:
    response = client.get("/api/v1/files/account-export")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/files/template-download")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/files/log-export")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_files_endpoints_contract(auth_client, monkeypatch) -> None:
    class _DummyExportResult:
        content = b"id,name\n1,alice\n"
        mimetype = "text/csv; charset=utf-8"
        filename = "export.csv"

    class _DummyAccountExportService:
        @staticmethod
        def export_accounts_csv(filters):  # noqa: ANN001
            del filters
            return _DummyExportResult()

    class _DummyInstancesExportService:
        @staticmethod
        def export_instances_csv(*, search: str, db_type: str):  # noqa: ANN001
            del search, db_type
            return _DummyExportResult()

    class _DummyLogsExportService:
        @staticmethod
        def list_logs(filters):  # noqa: ANN001
            del filters
            return []

    import app.api.v1.namespaces.files as api_module

    monkeypatch.setattr(api_module, "_account_export_service", _DummyAccountExportService())
    monkeypatch.setattr(api_module, "_instances_export_service", _DummyInstancesExportService())
    monkeypatch.setattr(api_module, "_logs_export_service", _DummyLogsExportService())
    monkeypatch.setattr(DatabaseLedgerService, "iterate_all", lambda self, search, db_type, tags: [])

    response = auth_client.get("/api/v1/files/account-export")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")
    assert response.mimetype in {"text/csv", "text/plain"}

    response = auth_client.get("/api/v1/files/instance-export")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")

    response = auth_client.get("/api/v1/files/database-ledger-export")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")

    response = auth_client.get("/api/v1/files/template-download")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")

    response = auth_client.get("/api/v1/files/log-export?format=json")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")
    assert response.mimetype == "application/json"

    response = auth_client.get("/api/v1/files/log-export?format=csv")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")
