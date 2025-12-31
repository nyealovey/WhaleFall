import pytest

from app.services.ledgers.database_ledger_service import DatabaseLedgerService


@pytest.mark.unit
def test_api_v1_databases_ledgers_requires_auth(client) -> None:
    response = client.get("/api/v1/databases/ledgers")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/databases/ledgers/1/capacity-trend")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_databases_ledgers_endpoints_contract(auth_client, monkeypatch) -> None:
    class _DummyLedgerResult:
        items = [
            {
                "id": 1,
                "database_name": "db1",
                "instance": {"id": 1, "name": "instance-1", "host": "127.0.0.1", "db_type": "mysql"},
                "db_type": "mysql",
                "capacity": {"size_mb": 1, "size_bytes": 1048576, "label": "1 MB", "collected_at": None},
                "sync_status": {"value": "completed", "label": "已更新", "variant": "success"},
                "tags": [],
            },
        ]
        total = 1
        page = 1
        limit = 20

    def _dummy_get_ledger(self, **kwargs):  # noqa: ANN001
        del self, kwargs
        return _DummyLedgerResult()

    def _dummy_get_capacity_trend(self, database_id: int, *, days=None):  # noqa: ANN001
        del database_id, days
        return {
            "database": {
                "id": 1,
                "name": "db1",
                "instance_id": 1,
                "instance_name": "instance-1",
                "db_type": "mysql",
            },
            "points": [
                {
                    "collected_at": "2025-01-01T00:00:00",
                    "collected_date": "2025-01-01",
                    "size_mb": 1,
                    "size_bytes": 1048576,
                    "label": "1 MB",
                },
            ],
        }

    monkeypatch.setattr(DatabaseLedgerService, "get_ledger", _dummy_get_ledger)
    monkeypatch.setattr(DatabaseLedgerService, "get_capacity_trend", _dummy_get_capacity_trend)

    response = auth_client.get("/api/v1/databases/ledgers?db_type=all&page=1&limit=20&search=db")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "per_page"}.issubset(data.keys())
    items = data.get("items")
    assert isinstance(items, list)
    assert len(items) == 1

    item = items[0]
    assert isinstance(item, dict)
    assert {
        "id",
        "database_name",
        "instance",
        "db_type",
        "capacity",
        "sync_status",
        "tags",
    }.issubset(item.keys())

    response = auth_client.get("/api/v1/databases/ledgers/1/capacity-trend?days=7")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"database", "points"}.issubset(data.keys())
