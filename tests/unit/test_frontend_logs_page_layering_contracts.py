from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_logs_page_template_must_load_logs_store_before_entry_script() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "app/templates/history/logs/logs.html"
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert "js/modules/stores/logs_store.js" in content, "LogsPage 模板必须加载 logs_store.js"
    assert content.index("js/modules/stores/logs_store.js") < content.index(
        "js/modules/views/history/logs/logs.js"
    ), "logs_store.js 必须在 logs.js 之前加载"


@pytest.mark.unit
def test_logs_page_entry_must_not_call_logs_service_methods_directly() -> None:
    """LogsPage 入口脚本必须通过 store/actions 驱动，不得直连 LogsService 方法。"""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/history/logs/logs.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createLogsStore" in content, "LogsPage 必须引入并使用 createLogsStore"
    assert "fetchStats(" not in content, "LogsPage 不得直接调用 LogsService.fetchStats"
    assert "fetchLogDetail(" not in content, "LogsPage 不得直接调用 LogsService.fetchLogDetail"
    assert "getGridUrl(" not in content, "LogsPage 不得直接调用 LogsService.getGridUrl"

