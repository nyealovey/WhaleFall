"""实例统计页卡片语义契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instances_statistics_template_uses_new_top_cards_and_current_for_distributions() -> None:
    content = _read_text("app/templates/instances/statistics.html")

    required_fragments = (
        "{% set total_instances = stats.total_instances or 0 %}",
        "{% set current_instances = stats.current_instances or 0 %}",
        "{% set audit_enabled_instances = stats.audit_enabled_instances or 0 %}",
        "{% set managed_instances = stats.managed_instances or 0 %}",
        "{% set unmanaged_instances = stats.unmanaged_instances or 0 %}",
        "{% set backed_up_instances = stats.backed_up_instances or 0 %}",
        "{% set backup_stale_instances = stats.backup_stale_instances or 0 %}",
        "{% set not_backed_up_instances = stats.not_backed_up_instances or 0 %}",
        "{% set audit_enabled_rate = (audit_enabled_instances / active_instances * 100) if active_instances else 0 %}",
        "{% set managed_rate = (managed_instances / current_instances * 100) if current_instances else 0 %}",
        "{% set backed_up_rate = (backed_up_instances / current_instances * 100) if current_instances else 0 %}",
        "{% set percent = (stat.count / current_instances * 100) if current_instances > 0 else 0 %}",
        "metric_card('实例总数'",
        'id="instancesMetaActiveCount"',
        'id="instancesMetaInactiveCount"',
        'id="instancesMetaDeletedCount"',
        "metric_card('审计信息'",
        "data_stat_key='audit_enabled_instances'",
        'id="instancesMetaAuditEnabledRate"',
        "metric_card('托管统计'",
        "data_stat_key='managed_instances'",
        'id="instancesMetaManagedRate"',
        'id="instancesMetaUnmanagedCount"',
        "metric_card('备份统计'",
        "data_stat_key='backed_up_instances'",
        'id="instancesMetaBackedUpRate"',
        'id="instancesMetaBackupStaleCount"',
        'id="instancesMetaNotBackedUpCount"',
        "备份状态分布",
        'id="backupStatusChart"',
        "data-backup-status-stats",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "metric_card('高可用占比'" not in content
    assert "metric_card('数据库类型'" not in content


def test_instances_statistics_frontend_uses_new_card_fields_and_store_defaults() -> None:
    stats_js = _read_text("app/static/js/modules/views/instances/statistics.js")
    store_js = _read_text("app/static/js/modules/stores/instance_store.js")

    stats_fragments = (
        "setStatValue('audit_enabled_instances', stats.audit_enabled_instances);",
        "setStatValue('managed_instances', stats.managed_instances);",
        "setStatValue('backed_up_instances', stats.backed_up_instances);",
        "const current = Number(stats?.current_instances ?? 0) || 0;",
        "const auditEnabled = Number(stats?.audit_enabled_instances ?? 0) || 0;",
        "const managed = Number(stats?.managed_instances ?? 0) || 0;",
        "const backedUp = Number(stats?.backed_up_instances ?? 0) || 0;",
        "const backupStale = Number(stats?.backup_stale_instances ?? 0) || 0;",
        "const notBackedUp = Number(stats?.not_backed_up_instances ?? 0) || 0;",
        "setText('instancesMetaActiveCount'",
        "setText('instancesMetaDeletedCount'",
        "formatPercent(active > 0 ? auditEnabled / active : 0",
        "formatPercent(current > 0 ? managed / current : 0",
        "formatPercent(current > 0 ? backedUp / current : 0",
        "setText('instancesMetaUnmanagedCount'",
        "setText('instancesMetaBackupStaleCount'",
        "setText('instancesMetaNotBackedUpCount'",
        "let backupStatusChart = null;",
        "createBackupStatusChart();",
        "updateBackupStatusChart(stats.backup_status_stats);",
    )
    for fragment in stats_fragments:
        assert fragment in stats_js

    assert "current_instances: 0," in store_js
    assert "audit_enabled_instances: 0," in store_js
    assert "managed_instances: 0," in store_js
    assert "backed_up_instances: 0," in store_js
    assert "backup_stale_instances: 0," in store_js
    assert "not_backed_up_instances: 0," in store_js
