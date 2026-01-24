from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_accounts_statistics_template_must_load_store_before_entry_script() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    template_path = repo_root / "app/templates/accounts/statistics.html"
    content = template_path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "js/modules/stores/accounts_statistics_store.js" in content
    ), "AccountsStatisticsPage 模板必须加载 accounts_statistics_store.js"
    assert content.index("js/modules/stores/accounts_statistics_store.js") < content.index(
        "js/modules/views/accounts/statistics.js"
    ), "accounts_statistics_store.js 必须在 statistics.js 之前加载"


@pytest.mark.unit
def test_accounts_statistics_entry_must_not_call_service_directly() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/accounts/statistics.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert (
        "createAccountsStatisticsStore" in content
    ), "AccountsStatisticsPage 必须引入并使用 createAccountsStatisticsStore"
    assert "fetchStatistics(" not in content, "AccountsStatisticsPage 不得直连 AccountsStatisticsService.fetchStatistics"

