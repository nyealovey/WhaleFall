import pytest

import app.api.v1.namespaces.accounts as accounts_api
import app.api.v1.namespaces.instances as instances_api
from app.services.ledgers.database_ledger_service import DatabaseLedgerService


@pytest.mark.unit
def test_api_v1_files_requires_auth(client) -> None:
    for path in (
        "/api/v1/accounts/ledgers/exports",
        "/api/v1/instances/exports",
        "/api/v1/databases/ledgers/exports",
        "/api/v1/instances/imports/template",
    ):
        response = client.get(path)
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
        def export_accounts_csv(filters):
            del filters
            return _DummyExportResult()

    class _DummyInstancesExportService:
        @staticmethod
        def export_instances_csv(*, search: str, db_type: str):
            del search, db_type
            return _DummyExportResult()

    monkeypatch.setattr(accounts_api, "_account_export_service", _DummyAccountExportService())
    monkeypatch.setattr(instances_api, "_instances_export_service", _DummyInstancesExportService())
    monkeypatch.setattr(
        DatabaseLedgerService,
        "iterate_all",
        lambda self, *, search, db_type, instance_id=None, tags=None: [],  # noqa: ARG005
    )

    response = auth_client.get("/api/v1/accounts/ledgers/exports")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")
    assert response.mimetype in {"text/csv", "text/plain"}

    response = auth_client.get("/api/v1/instances/exports")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")

    response = auth_client.get("/api/v1/databases/ledgers/exports")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")

    response = auth_client.get("/api/v1/instances/imports/template")
    assert response.status_code == 200
    assert "attachment" in (response.headers.get("Content-Disposition") or "")
