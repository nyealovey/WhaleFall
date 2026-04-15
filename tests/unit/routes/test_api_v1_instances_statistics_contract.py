import pytest

import app.api.v1.namespaces.instances as api_module
from app.api.v1.restx_models.instances import INSTANCE_STATISTICS_FIELDS


@pytest.mark.unit
def test_api_v1_instances_statistics_requires_auth(client) -> None:
    response = client.get("/api/v1/instances/statistics")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_instances_statistics_contract(auth_client, monkeypatch) -> None:
    def _dummy_build_statistics():
        return {
            "total_instances": 2,
            "current_instances": 1,
            "active_instances": 1,
            "normal_instances": 1,
            "disabled_instances": 0,
            "deleted_instances": 1,
            "inactive_instances": 0,
            "audit_enabled_instances": 1,
            "high_availability_instances": 1,
            "managed_instances": 1,
            "unmanaged_instances": 0,
            "backed_up_instances": 1,
            "backup_stale_instances": 0,
            "not_backed_up_instances": 0,
            "backup_status_stats": [
                {"backup_status": "backed_up", "count": 1},
                {"backup_status": "backup_stale", "count": 0},
                {"backup_status": "not_backed_up", "count": 0},
            ],
            "db_types_count": 1,
            "db_type_stats": [{"db_type": "mysql", "count": 1}],
            "port_stats": [{"port": 3306, "count": 1}],
            "version_stats": [{"db_type": "mysql", "version": "8", "count": 1}],
        }

    monkeypatch.setattr(api_module, "_build_instance_statistics", _dummy_build_statistics, raising=False)

    response = auth_client.get("/api/v1/instances/statistics")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {
        "total_instances",
        "current_instances",
        "active_instances",
        "normal_instances",
        "disabled_instances",
        "deleted_instances",
        "inactive_instances",
        "audit_enabled_instances",
        "high_availability_instances",
        "managed_instances",
        "unmanaged_instances",
        "backed_up_instances",
        "backup_stale_instances",
        "not_backed_up_instances",
        "backup_status_stats",
        "db_types_count",
        "db_type_stats",
        "port_stats",
        "version_stats",
    }.issubset(data.keys())

    assert data["backup_status_stats"] == [
        {"backup_status": "backed_up", "count": 1},
        {"backup_status": "backup_stale", "count": 0},
        {"backup_status": "not_backed_up", "count": 0},
    ]

    for field in (
        "managed_instances",
        "unmanaged_instances",
        "backed_up_instances",
        "backup_stale_instances",
        "not_backed_up_instances",
        "backup_status_stats",
    ):
        assert field in INSTANCE_STATISTICS_FIELDS
