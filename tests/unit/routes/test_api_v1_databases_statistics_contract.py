import pytest

import app.api.v1.namespaces.databases as api_module


@pytest.mark.unit
def test_api_v1_databases_statistics_requires_auth(client) -> None:
    response = client.get("/api/v1/databases/statistics")
    assert response.status_code == 401

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_databases_statistics_contract(auth_client, monkeypatch) -> None:
    def _dummy_build_database_statistics():
        return {
            "total_databases": 8,
            "active_databases": 6,
            "inactive_databases": 1,
            "deleted_databases": 2,
            "total_instances": 3,
            "total_size_mb": 4096,
            "avg_size_mb": 682.7,
            "max_size_mb": 2048,
            "db_type_stats": [
                {"db_type": "mysql", "count": 4},
                {"db_type": "postgresql", "count": 2},
            ],
            "instance_stats": [
                {"instance_id": 1, "instance_name": "prod-mysql-1", "db_type": "mysql", "count": 3},
            ],
            "sync_status_stats": [
                {"value": "completed", "label": "已更新", "variant": "success", "count": 4},
                {"value": "pending", "label": "待采集", "variant": "secondary", "count": 2},
            ],
            "capacity_rankings": [
                {
                    "instance_id": 1,
                    "instance_name": "prod-mysql-1",
                    "db_type": "mysql",
                    "database_name": "app_db",
                    "size_mb": 2048,
                    "size_label": "2.00 GB",
                    "collected_at": "2026-03-16T10:00:00+00:00",
                },
            ],
        }

    monkeypatch.setattr(api_module, "_build_database_statistics", _dummy_build_database_statistics, raising=False)

    response = auth_client.get("/api/v1/databases/statistics")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    stats = data.get("stats")
    assert isinstance(stats, dict)
    assert {
        "total_databases",
        "active_databases",
        "inactive_databases",
        "deleted_databases",
        "total_instances",
        "total_size_mb",
        "avg_size_mb",
        "max_size_mb",
        "db_type_stats",
        "instance_stats",
        "sync_status_stats",
        "capacity_rankings",
    }.issubset(stats.keys())
