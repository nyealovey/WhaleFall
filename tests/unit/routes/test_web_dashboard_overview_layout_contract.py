"""Web 仪表盘页面布局契约测试.

目标:
- 仪表盘采用新的控制台叙事结构，而不是普通 4 卡 + 8/4 分栏后台布局
- 关键区域具备稳定的 HTML 骨架，便于样式和脚本继续演进
"""

from __future__ import annotations

import pytest


def _fake_overview() -> dict:
    return {
        "instances": {"total": 12, "active": 11, "inactive": 1, "deleted": 0},
        "accounts": {"total": 28, "active": 21, "locked": 3},
        "capacity": {"total_gb": 6144},
        "databases": {"total": 19, "active": 18, "inactive": 1},
    }


def _fake_charts() -> dict:
    return {
        "logs": [
            {"date": "03-10", "error_count": 3, "warning_count": 6},
            {"date": "03-11", "error_count": 1, "warning_count": 5},
        ]
    }


def _fake_status() -> dict:
    return {
        "system": {
            "cpu": 38.2,
            "memory": {"percent": 64.1},
            "disk": {"percent": 48.6},
        },
        "services": {
            "database": "healthy",
            "redis": "healthy",
        },
        "uptime": "3 天 12 小时",
    }


@pytest.mark.unit
def test_web_dashboard_page_renders_console_storytelling_layout(auth_client, monkeypatch) -> None:
    monkeypatch.setattr("app.routes.dashboard.get_system_overview", _fake_overview)
    monkeypatch.setattr("app.routes.dashboard.get_chart_data", _fake_charts)
    monkeypatch.setattr("app.routes.dashboard.get_system_status", _fake_status)

    response = auth_client.get("/dashboard/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)

    required_fragments = (
        'class="dashboard-overview"',
        "dashboard-hero",
        "dashboard-command",
        "dashboard-primary-metrics",
        "dashboard-focus-grid",
        "dashboard-chart-panel",
        "dashboard-health-panel",
        "dashboard-risk-panel",
        "dashboard-signal-strip",
        'data-chart-status="',
    )

    for fragment in required_fragments:
        assert fragment in html

    assert "dashboard-layout" not in html
