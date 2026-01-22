from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_capacity_templates_use_metric_card() -> None:
    """容量统计页的顶部指标卡必须使用 MetricCard（不再使用 stats_card 旧组件）。"""
    repo_root = Path(__file__).resolve().parents[2]
    templates = [
        repo_root / "app/templates/capacity/databases.html",
        repo_root / "app/templates/capacity/instances.html",
    ]

    for template in templates:
        content = template.read_text(encoding="utf-8", errors="ignore")
        assert "metric_card(" in content, f"{template.name} 未使用 metric_card 宏"
        assert "stats_card" not in content, f"{template.name} 仍在使用 stats_card 旧宏"
