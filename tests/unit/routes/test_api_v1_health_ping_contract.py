# tests/unit/routes/test_api_v1_health_ping_contract.py
"""API v1 health contract tests."""

import pytest


@pytest.mark.unit
def test_api_v1_health_ping_returns_success_envelope(client):
    response = client.get("/api/v1/health/ping")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload["success"] is True
    assert payload["error"] is False
    assert payload["message"] == "健康检查成功"
    assert payload["data"]["status"] == "ok"


@pytest.mark.unit
def test_api_v1_health_basic_returns_success_envelope(client):
    response = client.get("/api/v1/health/basic")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload["success"] is True
    assert payload["error"] is False
    assert payload["message"] == "服务运行正常"

    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("status") == "healthy"
    assert data.get("version") == "1.0.7"
    assert isinstance(data.get("timestamp"), float)


@pytest.mark.unit
def test_api_v1_health_health_returns_success_envelope(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload["success"] is True
    assert payload["error"] is False
    assert payload["message"] == "操作成功"

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"status", "database", "redis", "timestamp", "uptime"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_health_unknown_path_returns_error_envelope(client):
    response = client.get("/api/v1/health/does-not-exist")

    assert response.status_code == 404
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "INVALID_REQUEST"
