from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_sync_sessions_page_template_must_load_store_before_entry_script() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "app/templates/history/sessions/sync-sessions.html"
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "js/modules/stores/task_runs_store.js" in content
    ), "SyncSessionsPage 模板必须加载 task_runs_store.js"
    assert content.index("js/modules/stores/task_runs_store.js") < content.index(
        "js/modules/views/history/sessions/sync-sessions.js"
    ), "task_runs_store.js 必须在 sync-sessions.js 之前加载"


@pytest.mark.unit
def test_sync_sessions_page_entry_must_not_call_service_methods_directly() -> None:
    """SyncSessionsPage 必须通过 store/actions 驱动，不得直连 TaskRunsService 方法。"""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/history/sessions/sync-sessions.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "createTaskRunsStore" in content
    ), "SyncSessionsPage 必须引入并使用 createTaskRunsStore"
    assert "getGridUrl(" not in content, "SyncSessionsPage 不得直接调用 getGridUrl"
    assert ".detail(" not in content, "SyncSessionsPage 不得直接调用 TaskRunsService.detail"
    assert ".cancel(" not in content, "SyncSessionsPage 不得直接调用 TaskRunsService.cancel"

