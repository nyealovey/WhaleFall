from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_session_detail_maps_email_alert_display_states_to_non_success_labels() -> None:
    content = _read_text("app/static/js/modules/views/history/sessions/session-detail.js")

    assert "function getRunStatusMeta(run)" in content
    assert "case 'no_event':" in content
    assert "text: '无事件'" in content
    assert "case 'already_sent':" in content
    assert "text: '已发送过'" in content
    assert "case 'skipped_no_event':" in content
    assert "case 'skipped_already_sent':" in content
    assert "text: '已跳过'" in content
