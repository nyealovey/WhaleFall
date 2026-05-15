from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_risk_center_cards_use_six_column_desktop_grid() -> None:
    css = _read_text("app/static/css/pages/risk-center.css")

    assert ".risk-card-grid {" in css
    assert "grid-template-columns: repeat(6, minmax(0, 1fr));" in css
    assert "grid-template-columns: repeat(auto-fill" not in css


def test_risk_center_cards_use_compact_task_failure_notice() -> None:
    template = _read_text("app/templates/risk_center/index.html")
    script = _read_text("app/static/js/modules/views/risk-center/index.js")
    css = _read_text("app/static/css/pages/risk-center.css")

    combined_ui_sources = f"{template}\n{script}\n{css}"
    assert "risk-instance-card__flags" not in combined_ui_sources
    assert "risk-instance-card__status" not in combined_ui_sources
    assert "renderFlags" not in script
    assert "status_band" not in script
    assert "risk-instance-card__task" in template
    assert "risk-instance-card__task" in script
    assert "risk-instance-card__task" in css
    assert "card.tasks.tone != 'success'" in template
