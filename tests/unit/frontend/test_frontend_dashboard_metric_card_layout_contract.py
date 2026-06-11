"""系统仪表板统计卡布局契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_dashboard_overview_metrics_use_4up_grid() -> None:
    content = _read_text("app/templates/dashboard/overview.html")

    assert "dashboard-metrics row row-cols-1 row-cols-md-2 row-cols-xl-4" in content


def test_dashboard_overview_css_forces_metric_cards_to_fill_each_column() -> None:
    content = _read_text("app/static/css/pages/dashboard/overview.css")

    assert ".dashboard-metrics .col > .wf-metric-card" in content
    assert "width: 100%;" in content
    assert "flex: 1 1 auto;" in content


def test_metric_card_baseline_does_not_take_dashboard_specific_width_rule() -> None:
    content = _read_text("app/static/css/components/metric-card.css")

    assert "flex: 1 1 auto;" not in content
