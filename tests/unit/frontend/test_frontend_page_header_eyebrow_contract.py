"""页面头部 eyebrow 文案契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_page_headers_override_default_control_surface_copy() -> None:
    cases = {
        "app/templates/dashboard/overview.html": "eyebrow='System Overview'",
        "app/templates/capacity/instances.html": "eyebrow='Instance Capacity'",
        "app/templates/capacity/databases.html": "eyebrow='Database Capacity'",
        "app/templates/credentials/list.html": "eyebrow='Credential Vault'",
        "app/templates/auth/list.html": "eyebrow='User Administration'",
        "app/templates/admin/partitions/index.html": "eyebrow='Partition Operations'",
        "app/templates/accounts/statistics.html": "eyebrow='Account Insights'",
        "app/templates/history/logs/logs.html": "eyebrow='Log Monitoring'",
        "app/templates/accounts/classification_statistics.html": "eyebrow='Classification Analytics'",
        "app/templates/accounts/ledgers.html": "eyebrow='Account Ledger'",
        "app/templates/instances/statistics.html": "eyebrow='Instance Insights'",
        "app/templates/databases/ledgers.html": "eyebrow='Database Ledger'",
        "app/templates/instances/list.html": "eyebrow='Instance Registry'",
        "app/templates/accounts/account-classification/index.html": "eyebrow='Classification Registry'",
        "app/templates/tags/index.html": "eyebrow='Tag Registry'",
        "app/templates/admin/scheduler/index.html": "eyebrow='Scheduler Operations'",
        "app/templates/tags/bulk/assign.html": "eyebrow='Batch Tagging'",
        "app/templates/history/sessions/sync-sessions.html": "eyebrow='Operations Center'",
        "app/templates/history/account_change_logs/account-change-logs.html": "eyebrow='Change Audit'",
    }

    for path, expected_fragment in cases.items():
        content = _read_text(path)
        assert expected_fragment in content, f"{path} 缺少 {expected_fragment}"
