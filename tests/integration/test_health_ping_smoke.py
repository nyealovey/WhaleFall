"""Integration smoke tests.

这些测试需要显式配置真实数据库（见 tests/integration/conftest.py），用于确保 integration
目录不是“空壳”并能在 CI/本地按需运行。
"""

import pytest


@pytest.mark.integration
def test_api_v1_health_ping_returns_success_envelope(client):
    response = client.get("/api/v1/health/ping")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload["success"] is True
    assert payload["error"] is False
    assert payload["message"] == "健康检查成功"
    assert payload["data"]["status"] == "ok"

