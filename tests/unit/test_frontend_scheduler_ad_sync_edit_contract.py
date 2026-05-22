from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_scheduler_edit_modal_includes_ad_sync_function_option() -> None:
    content = _read_text("app/templates/admin/scheduler/modals/scheduler-modals.html")

    assert '<option value="sync_ad_accounts">AD 域账户同步</option>' in content


def test_scheduler_edit_modal_builtin_id_list_includes_ad_sync() -> None:
    content = _read_text("app/static/js/modules/views/admin/scheduler/modals/scheduler-modals.js")

    assert "'sync_ad_accounts'" in content
