from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_all_inventory_4up_pages_use_metric_card() -> None:
    """按 inventory：所有“顶部 4 卡”页面必须使用 MetricCard（替换掉各自私有 stat-card 体系）。"""

    repo_root = Path(__file__).resolve().parents[2]

    targets = {
        "template": [
            "app/templates/accounts/statistics.html",
            "app/templates/instances/statistics.html",
            "app/templates/admin/partitions/index.html",
            "app/templates/history/account_change_logs/account-change-logs.html",
        ],
        "css": [
            "app/static/css/pages/accounts/statistics.css",
            "app/static/css/pages/instances/statistics.css",
            "app/static/css/pages/admin/partitions.css",
            "app/static/css/pages/history/account-change-logs.css",
        ],
        "js": [
            "app/static/js/modules/views/accounts/statistics.js",
            "app/static/js/modules/views/instances/statistics.js",
            "app/static/js/modules/views/admin/partitions/index.js",
        ],
    }

    forbidden_tokens = [
        "account-stat-card",
        "instance-stat-card",
        "partition-stat-card",
        "change-log-stats-card",
    ]

    for rel_path in targets["template"]:
        content = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
        assert "metric_card(" in content, f"{rel_path} 未使用 metric_card 宏"
        for token in forbidden_tokens:
            assert token not in content, f"{rel_path} 仍包含旧指标卡私有 class: {token}"

    for rel_path in targets["css"]:
        content = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            assert token not in content, f"{rel_path} 仍包含旧指标卡私有样式: {token}"

    js_expect_no_selectors = [
        "data-stat-value",
        "[data-stat=\"",
    ]
    js_expect_selector = "data-stat-key"

    for rel_path in targets["js"]:
        content = (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")
        for selector in js_expect_no_selectors:
            assert selector not in content, f"{rel_path} 仍在依赖旧 selector: {selector}"
        assert js_expect_selector in content, f"{rel_path} 应使用 data-stat-key 作为 MetricCard 更新锚点"

