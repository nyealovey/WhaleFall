from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_scheduler_page_uses_shared_button_loading_without_local_dom_fallback() -> None:
    content = _read_text("app/static/js/modules/views/admin/scheduler/index.js")

    assert "withButtonLoading" in content
    assert "purgeButton.innerHTML" not in content
    assert "dataset.uiOriginalHtml" not in content
    assert "dataset.uiOriginalDisabled" not in content
    assert "node.innerHTML = ''" not in content
    assert "fas fa-spinner fa-spin" not in content


def test_scheduler_page_does_not_export_unimplemented_log_entry() -> None:
    content = _read_text("app/static/js/modules/views/admin/scheduler/index.js")

    assert "function viewJobLogs" not in content
    assert "window.viewJobLogs" not in content
    assert "日志查看功能待实现" not in content
