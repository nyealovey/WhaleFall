from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_history_and_scheduler_pages_use_metric_card() -> None:
    """日志/会话/调度页面的顶部指标卡必须使用 MetricCard，禁止私有 *-stats-card 体系。"""
    repo_root = Path(__file__).resolve().parents[2]
    targets = {
        "logs.html": repo_root / "app/templates/history/logs/logs.html",
        "sync-sessions.html": repo_root / "app/templates/history/sessions/sync-sessions.html",
        "scheduler/index.html": repo_root / "app/templates/admin/scheduler/index.html",
    }

    for name, path in targets.items():
        content = path.read_text(encoding="utf-8", errors="ignore")
        assert "metric_card(" in content, f"{name} 必须使用 metric_card 宏"

    assert "log-stats-card" not in targets["logs.html"].read_text(encoding="utf-8", errors="ignore")
    assert "session-stats-card" not in targets["sync-sessions.html"].read_text(encoding="utf-8", errors="ignore")
    assert "scheduler-stat-card" not in targets["scheduler/index.html"].read_text(encoding="utf-8", errors="ignore")

