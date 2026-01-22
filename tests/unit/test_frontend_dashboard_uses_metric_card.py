from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_dashboard_overview_uses_metric_card() -> None:
    """Dashboard 顶部指标卡必须使用 MetricCard，禁止 dashboard-stat-card 私有体系。"""
    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "app/templates/dashboard/overview.html"
    content = template.read_text(encoding="utf-8", errors="ignore")

    assert "dashboard-stat-card" not in content, "dashboard/overview.html 不应再使用 dashboard-stat-card"
    assert "metric_card(" in content, "dashboard/overview.html 必须使用 metric_card 宏"

