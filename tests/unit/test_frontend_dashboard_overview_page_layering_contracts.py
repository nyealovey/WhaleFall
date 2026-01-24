from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_dashboard_overview_template_must_load_store_before_entry_script() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "app/templates/dashboard/overview.html"
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "js/modules/stores/dashboard_store.js" in content
    ), "DashboardOverviewPage 模板必须加载 dashboard_store.js"
    assert content.index("js/modules/stores/dashboard_store.js") < content.index(
        "js/modules/views/dashboard/overview.js"
    ), "dashboard_store.js 必须在 overview.js 之前加载"


@pytest.mark.unit
def test_dashboard_overview_entry_must_not_call_dashboard_service_directly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/dashboard/overview.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createDashboardStore" in content, "DashboardOverviewPage 必须引入并使用 createDashboardStore"
    assert "fetchCharts(" not in content, "DashboardOverviewPage 不得直连 DashboardService.fetchCharts"

