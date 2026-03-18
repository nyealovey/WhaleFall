from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_scheduler_edit_modal_includes_email_alert_function_option() -> None:
    content = _read_text("app/templates/admin/scheduler/modals/scheduler-modals.html")

    assert '<option value="email_alert">邮件告警汇总</option>' in content
    assert 'value="send_email_alert_digest"' not in content


def test_scheduler_edit_modal_builtin_id_list_includes_email_alert() -> None:
    content = _read_text("app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js")

    assert "'email_alert'" in content
    assert "'calculate_database'" in content
    assert "'calculate_account'" in content

    assert "'send_email_alert_digest'" not in content
    assert "'calculate_database_aggregations'" not in content
    assert "'calculate_account_classification'" not in content
