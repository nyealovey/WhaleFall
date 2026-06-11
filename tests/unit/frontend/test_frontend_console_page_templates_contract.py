"""剩余控制台页面模板契约测试.

目标:
- 剩余列表页统一接入新的 list shell
- 剩余统计页统一接入新的 stats shell
- 批量与工作台页面统一接入新的 workbench shell
"""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_remaining_list_pages_use_console_list_shell() -> None:
    cases = {
        "app/templates/credentials/list.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/instances/list.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/accounts/ledgers.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/databases/ledgers.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/auth/list.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/history/logs/logs.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/history/account_change_logs/account-change-logs.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
        "app/templates/history/sessions/sync-sessions.html": (
            "console-list-page",
            "console-command-deck",
            "console-filter-shell",
            "console-grid-shell",
        ),
    }

    for path, required_fragments in cases.items():
        content = _read_text(path)
        for fragment in required_fragments:
            assert fragment in content, f"{path} 缺少 {fragment}"


def test_remaining_stats_pages_use_console_stats_shell() -> None:
    cases = {
        "app/templates/capacity/instances.html": (
            "console-stats-page",
            "console-command-deck",
            "console-context-strip",
            "console-analysis-shell",
        ),
        "app/templates/capacity/databases.html": (
            "console-stats-page",
            "console-command-deck",
            "console-context-strip",
            "console-analysis-shell",
        ),
        "app/templates/instances/statistics.html": (
            "console-stats-page",
            "console-command-deck",
            "console-context-strip",
            "console-analysis-shell",
        ),
        "app/templates/accounts/statistics.html": (
            "console-stats-page",
            "console-command-deck",
            "console-context-strip",
            "console-analysis-shell",
        ),
        "app/templates/accounts/classification_statistics.html": (
            "console-stats-page",
            "console-command-deck",
            "console-filter-shell",
            "console-analysis-shell",
        ),
        "app/templates/admin/partitions/index.html": (
            "console-stats-page",
            "console-command-deck",
            "console-context-strip",
            "console-analysis-shell",
        ),
    }

    for path, required_fragments in cases.items():
        content = _read_text(path)
        for fragment in required_fragments:
            assert fragment in content, f"{path} 缺少 {fragment}"


def test_bulk_assign_page_uses_console_workbench_shell() -> None:
    content = _read_text("app/templates/tags/bulk/assign.html")

    required_fragments = (
        "console-workbench-page",
        "console-command-deck",
        "console-workbench-grid",
        "console-rail-card",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_global_css_defines_console_shell_primitives() -> None:
    content = _read_text("app/static/css/global.css")

    required_fragments = (
        ".console-list-page",
        ".console-stats-page",
        ".console-workbench-page",
        ".console-command-deck",
        ".console-context-strip",
        ".console-filter-shell",
        ".console-grid-shell",
        ".console-analysis-shell",
        ".console-workbench-grid",
        ".console-rail-card",
    )

    for fragment in required_fragments:
        assert fragment in content
