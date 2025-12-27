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
