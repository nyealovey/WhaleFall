from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_risk_center_cards_use_four_column_desktop_grid() -> None:
    css = _read_text("app/static/css/pages/risk-center.css")

    assert ".risk-card-grid {" in css
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css
    assert "grid-template-columns: repeat(auto-fill" not in css
    assert "grid-template-columns: repeat(6, minmax(0, 1fr));" not in css


def test_risk_center_cards_hide_action_menu_and_use_db_type_icon() -> None:
    template = _read_text("app/templates/risk_center/index.html")
    script = _read_text("app/static/js/modules/views/risk-center/index.js")
    css = _read_text("app/static/css/pages/risk-center.css")

    combined_ui_sources = f"{template}\n{script}\n{css}"
    assert "risk-instance-card__flags" not in combined_ui_sources
    assert "risk-instance-card__status" not in combined_ui_sources
    assert "dropdown-menu" not in template
    assert "dropdown-menu" not in script
    assert "fa-ellipsis-v" not in template
    assert "fa-ellipsis-v" not in script
    assert "risk-instance-card__db-type" in template
    assert "risk-instance-card__db-type" in script
    assert "risk-instance-card__db-type" in css
    assert "risk-instance-card__db-type-asset" in template
    assert "asset_url" in template
    assert "renderDbTypeIcon" in script


def test_risk_center_cards_render_tasks_as_fourth_metric() -> None:
    template = _read_text("app/templates/risk_center/index.html")
    script = _read_text("app/static/js/modules/views/risk-center/index.js")
    css = _read_text("app/static/css/pages/risk-center.css")

    assert "renderFlags" not in script
    assert "status_band" not in script
    assert "renderTaskNotice" not in script
    assert "risk-instance-card__task" not in template
    assert "risk-instance-card__task" not in script
    assert "risk-instance-card__task" not in css
    assert "card.tasks.label" in template
    assert 'renderMetric(card?.tasks, "任务")' in script
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css


def test_risk_center_summary_uses_four_visible_kpi_cards() -> None:
    template = _read_text("app/templates/risk_center/index.html")
    script = _read_text("app/static/js/modules/views/risk-center/index.js")
    css = _read_text("app/static/css/pages/risk-center.css")

    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css
    assert "metric_card('未知'" not in template
    assert "data_stat_key='unknown'" not in template
    assert "counts.unknown" not in script
    assert '<option value="unknown"' not in template
    assert '<option value="info"' not in template
    assert "metric_card('严重'" in template
    assert "metric_card('警告'" in template
    assert "metric_card('正常'" in template
    assert "metric_card('总实例'" in template
