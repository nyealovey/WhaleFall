from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _read_text(repo_root: Path, rel_path: str) -> str:
    return (repo_root / rel_path).read_text(encoding="utf-8", errors="ignore")


def test_frontend_metric_card_migration_contract() -> None:
    """MetricCard 迁移门禁（清单式）.

    目标:
    - 关键页面必须使用 MetricCard（避免 UI 体系回退）
    - 关键页面/资源不得残留旧私有 class/token（避免 selector/样式漂移）
    - 历史/调度等页面按 inventory 约定不再保留顶部 4 卡
    """

    repo_root = Path(__file__).resolve().parents[2]

    must_use_metric_card_templates = [
        # Dashboard
        "app/templates/dashboard/overview.html",
        # Capacity pages
        "app/templates/capacity/databases.html",
        "app/templates/capacity/instances.html",
        # Tags page
        "app/templates/tags/index.html",
        # History logs page
        "app/templates/history/logs/logs.html",
        # Inventory "4-up" pages
        "app/templates/accounts/statistics.html",
        "app/templates/instances/statistics.html",
        "app/templates/admin/partitions/index.html",
        "app/templates/history/account_change_logs/account-change-logs.html",
    ]

    forbidden_tokens_by_template: dict[str, list[str]] = {
        "app/templates/dashboard/overview.html": ["dashboard-stat-card"],
        "app/templates/tags/index.html": ["tags-stat-card"],
        "app/templates/history/logs/logs.html": ["log-stats-card"],
        "app/templates/accounts/statistics.html": ["account-stat-card"],
        "app/templates/instances/statistics.html": ["instance-stat-card"],
        "app/templates/admin/partitions/index.html": ["partition-stat-card"],
        "app/templates/history/account_change_logs/account-change-logs.html": ["change-log-stats-card"],
    }

    for rel_path in must_use_metric_card_templates:
        content = _read_text(repo_root, rel_path)
        assert "metric_card(" in content, f"{rel_path} 未使用 metric_card 宏"
        assert "stats_card" not in content, f"{rel_path} 仍在使用 stats_card 旧宏"

        for token in forbidden_tokens_by_template.get(rel_path, []):
            assert token not in content, f"{rel_path} 仍包含旧指标卡私有 token: {token}"

    # 按 inventory：这些页面不再保留顶部 4 卡（避免口径/术语不清导致的信息噪声）。
    must_not_use_metric_card_templates: dict[str, dict[str, list[str]]] = {
        "app/templates/history/sessions/sync-sessions.html": {
            "required": ['id="taskRunsTotalCount"'],
            "forbidden": ["session-stats-card"],
        },
        "app/templates/admin/scheduler/index.html": {
            "required": ['id="activeJobsCount"', 'id="pausedJobsCount"'],
            "forbidden": ["scheduler-stat-card"],
        },
    }

    for rel_path, rules in must_not_use_metric_card_templates.items():
        content = _read_text(repo_root, rel_path)
        assert "metric_card(" not in content, f"{rel_path} 不应保留顶部 MetricCard"
        for marker in rules["required"]:
            assert marker in content, f"{rel_path} 缺少必要标记: {marker}"
        for token in rules["forbidden"]:
            assert token not in content, f"{rel_path} 仍包含旧指标卡私有 token: {token}"

    # CSS：这些旧指标卡私有 class 不应再存在（避免样式/selector 回退）。
    forbidden_css_tokens = [
        "account-stat-card",
        "instance-stat-card",
        "partition-stat-card",
        "change-log-stats-card",
    ]
    css_targets = [
        "app/static/css/pages/accounts/statistics.css",
        "app/static/css/pages/instances/statistics.css",
        "app/static/css/pages/admin/partitions.css",
        "app/static/css/pages/history/account-change-logs.css",
    ]
    for rel_path in css_targets:
        content = _read_text(repo_root, rel_path)
        for token in forbidden_css_tokens:
            assert token not in content, f"{rel_path} 仍包含旧指标卡私有样式 token: {token}"

    # JS：页面更新锚点必须使用 MetricCard selector 体系（避免继续依赖旧 selector）。
    js_inventory_targets = [
        "app/static/js/modules/views/accounts/statistics.js",
        "app/static/js/modules/views/instances/statistics.js",
        "app/static/js/modules/views/admin/partitions/index.js",
    ]
    js_expect_no_selectors = [
        "data-stat-value",
        '[data-stat="',
    ]
    js_expect_selector = "data-stat-key"
    for rel_path in js_inventory_targets:
        content = _read_text(repo_root, rel_path)
        for selector in js_expect_no_selectors:
            assert selector not in content, f"{rel_path} 仍在依赖旧 selector: {selector}"
        assert js_expect_selector in content, f"{rel_path} 应使用 {js_expect_selector} 作为 MetricCard 更新锚点"

    tags_js = "app/static/js/modules/views/tags/index.js"
    tags_js_content = _read_text(repo_root, tags_js)
    assert ".tags-stat-card__value" not in tags_js_content, f"{tags_js} 不应再依赖 .tags-stat-card__value"
    assert "metric-value" in tags_js_content, f"{tags_js} 应使用 MetricCard 的 value selector"
