import pytest


@pytest.mark.unit
def test_api_v1_instances_statistics_requires_auth(client) -> None:
    response = client.get("/api/v1/instances/statistics")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_instances_statistics_contract(auth_client, monkeypatch) -> None:
    import app.api.v1.namespaces.instances as api_module

    def _dummy_build_statistics():
        return {
            "total_instances": 1,
            "active_instances": 1,
            "normal_instances": 1,
            "disabled_instances": 0,
            "deleted_instances": 0,
            "inactive_instances": 0,
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
        "active_instances",
        "normal_instances",
        "disabled_instances",
        "deleted_instances",
        "inactive_instances",
        "db_types_count",
        "db_type_stats",
        "port_stats",
        "version_stats",
    }.issubset(data.keys())
