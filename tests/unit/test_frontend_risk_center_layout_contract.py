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
