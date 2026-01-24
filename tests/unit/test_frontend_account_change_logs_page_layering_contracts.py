from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_account_change_logs_page_template_must_load_store_before_entry_script() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = (
        repo_root
        / "app/templates/history/account_change_logs/account-change-logs.html"
    )
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "js/modules/stores/account_change_logs_store.js" in content
    ), "AccountChangeLogsPage 模板必须加载 account_change_logs_store.js"
    assert content.index(
        "js/modules/stores/account_change_logs_store.js"
    ) < content.index(
        "js/modules/views/history/account-change-logs/account-change-logs.js"
    ), "account_change_logs_store.js 必须在 account-change-logs.js 之前加载"


@pytest.mark.unit
def test_account_change_logs_page_entry_must_not_call_service_methods_directly() -> None:
    """AccountChangeLogsPage 必须通过 store/actions 驱动，不得直连 Service 方法。"""
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/history/account-change-logs/account-change-logs.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "createAccountChangeLogsStore" in content
    ), "AccountChangeLogsPage 必须引入并使用 createAccountChangeLogsStore"
    assert "fetchStats(" not in content, "AccountChangeLogsPage 不得直接调用 fetchStats"
    assert "fetchDetail(" not in content, "AccountChangeLogsPage 不得直接调用 fetchDetail"
    assert "getGridUrl(" not in content, "AccountChangeLogsPage 不得直接调用 getGridUrl"

