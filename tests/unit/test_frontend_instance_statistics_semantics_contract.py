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
        "{% set high_availability_instances = stats.high_availability_instances or 0 %}",
        "{% set audit_enabled_rate = (audit_enabled_instances / active_instances * 100) if active_instances else 0 %}",
        "{% set high_availability_rate = (high_availability_instances / active_instances * 100) if active_instances else 0 %}",
        "{% set top_db_type_share = (top_db_type.count / current_instances * 100) if top_db_type and current_instances else 0 %}",
        "{% set percent = (stat.count / current_instances * 100) if current_instances > 0 else 0 %}",
        "metric_card('实例总数'",
        'id="instancesMetaActiveCount"',
        'id="instancesMetaInactiveCount"',
        'id="instancesMetaDeletedCount"',
        "metric_card('审计信息'",
        "data_stat_key='audit_enabled_instances'",
        'id="instancesMetaAuditEnabledRate"',
        "metric_card('高可用占比'",
        "data_stat_key='high_availability_instances'",
        'id="instancesMetaHighAvailabilityRate"',
        "metric_card('数据库类型'",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_instances_statistics_frontend_uses_new_card_fields_and_store_defaults() -> None:
    stats_js = _read_text("app/static/js/modules/views/instances/statistics.js")
    store_js = _read_text("app/static/js/modules/stores/instance_store.js")

    stats_fragments = (
        "setStatValue('audit_enabled_instances', stats.audit_enabled_instances);",
        "setStatValue('high_availability_instances', stats.high_availability_instances);",
        "const current = Number(stats?.current_instances ?? 0) || 0;",
        "const auditEnabled = Number(stats?.audit_enabled_instances ?? 0) || 0;",
        "const highAvailability = Number(stats?.high_availability_instances ?? 0) || 0;",
        "setText('instancesMetaActiveCount'",
        "setText('instancesMetaDeletedCount'",
        "formatPercent(active > 0 ? auditEnabled / active : 0",
        "formatPercent(active > 0 ? highAvailability / active : 0",
        "formatPercent(current > 0 ? topCount / current : 0",
    )
    for fragment in stats_fragments:
        assert fragment in stats_js

    assert "current_instances: 0," in store_js
    assert "audit_enabled_instances: 0," in store_js
    assert "high_availability_instances: 0," in store_js
