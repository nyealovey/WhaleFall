"""Dashboard 与统计页状态语义契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_dashboard_overview_uses_account_normal_locked_deleted_and_database_normal_restricted_deleted() -> None:
    content = _read_text("app/templates/dashboard/overview.html")

    required_fragments = (
        "overview.accounts.normal",
        "overview.accounts.locked",
        "overview.accounts.deleted",
        "overview.databases.active",
        "overview.databases.inactive",
        "overview.databases.deleted",
    )
    for fragment in required_fragments:
        assert fragment in content

    forbidden_fragments = (
        "overview.accounts.active if overview and overview.accounts else 0 }} 活跃",
        "(overview.accounts.total - overview.accounts.active)",
        "overview.databases.inactive if overview and overview.databases else 0 }} 已删除",
    )
    for fragment in forbidden_fragments:
        assert fragment not in content


def test_accounts_statistics_template_uses_normal_locked_deleted_instead_of_active_rate_and_inactive() -> None:
    content = _read_text("app/templates/accounts/statistics.html")

    required_fragments = (
        "{% set normal_accounts = stats.normal_accounts or 0 %}",
        "{% set deleted_accounts = stats.deleted_accounts or 0 %}",
        "metric_card('总账户数'",
        'id="accountsMetaNormalCount"',
        'id="accountsMetaLockedCount"',
        'id="accountsMetaDeletedCount"',
        "metric_card('正常账户'",
        "data_stat_key='normal_accounts'",
        "metric_card('受限账户'",
        "data_stat_key='locked_accounts'",
        "metric_card('统计实例'",
    )
    for fragment in required_fragments:
        assert fragment in content

    forbidden_fragments = (
        "accountsMetaActiveRate",
        "accountsMetaLockedRate",
        "accountsMetaInactiveCount",
        "metric_card('活跃账户'",
        "metric_card('锁定账户'",
        "metric_card('在线实例'",
    )
    for fragment in forbidden_fragments:
        assert fragment not in content


def test_accounts_statistics_frontend_refresh_logic_uses_normal_locked_deleted_labels() -> None:
    content = _read_text("app/static/js/modules/views/accounts/statistics.js")

    required_fragments = (
        'setValue("normal_accounts", stats.normal_accounts);',
        'setValue("locked_accounts", stats.locked_accounts);',
        'setText("accountsMetaNormalCount",',
        'setText("accountsMetaLockedCount",',
        'setText("accountsMetaDeletedCount",',
        "const normal = Number(stats?.normal_accounts ?? 0) || 0;",
        "const deleted = Number(stats?.deleted_accounts ?? 0) || 0;",
        'tone === "success" ? "正常" : tone === "warning" ? "受限" : "删除"',
    )
    for fragment in required_fragments:
        assert fragment in content

    forbidden_fragments = (
        'setValue("active_accounts", stats.active_accounts);',
        "accountsMetaActiveRate",
        "accountsMetaLockedRate",
        "accountsMetaInactiveCount",
        'tone === "success" ? "活跃"',
    )
    for fragment in forbidden_fragments:
        assert fragment not in content


def test_databases_statistics_template_uses_normal_restricted_deleted_labels() -> None:
    content = _read_text("app/templates/databases/statistics.html")

    required_fragments = (
        'title="正常数据库"',
        'aria-label="正常数据库"',
        'title="受限数据库"',
        'aria-label="受限数据库"',
        'title="已删除数据库"',
    )
    for fragment in required_fragments:
        assert fragment in content

    forbidden_fragments = (
        'title="活跃数据库"',
        'aria-label="活跃数据库"',
        'title="停用数据库"',
        'aria-label="停用数据库"',
        "metric_card('活跃数据库'",
    )
    for fragment in forbidden_fragments:
        assert fragment not in content
