"""实例列表筛选入口契约测试."""

from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


@pytest.mark.unit
def test_instance_list_template_exposes_audit_managed_and_backup_filters() -> None:
    content = _read_text("app/templates/instances/list.html")
    route_content = _read_text("app/routes/instances/manage.py")

    required_fragments = (
        "select_filter('审计', 'audit_status', 'audit_status'",
        "audit_status_options",
        "select_filter('托管', 'managed_status', 'managed_status'",
        "managed_status_options",
        "select_filter('备份', 'backup_status', 'backup_status'",
        "backup_status_options",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert content.index("select_filter('托管'") < content.index("select_filter('备份'")
    assert content.index("select_filter('备份'") < content.index("tag_selector_filter(tag_options")

    audit_option_fragments = (
        '"value": "enabled", "label": "已启用"',
        '"value": "configured_disabled", "label": "已配置未启用"',
        '"value": "not_configured", "label": "未配置"',
    )

    for fragment in audit_option_fragments:
        assert fragment in route_content

    backup_option_fragments = (
        '"value": "backed_up", "label": "24h内备份"',
        '"value": "backup_stale", "label": "备份过期"',
        '"value": "not_backed_up", "label": "未备份"',
    )

    for fragment in backup_option_fragments:
        assert fragment in route_content


@pytest.mark.unit
def test_instance_list_js_syncs_audit_managed_and_backup_filters() -> None:
    content = _read_text("app/static/js/modules/views/instances/list.js")

    required_fragments = (
        "'audit_status'",
        "'managed_status'",
        "'backup_status'",
        "audit_status: sanitizeText(source?.audit_status)",
        "managed_status: sanitizeText(source?.managed_status)",
        "backup_status: sanitizeText(source?.backup_status)",
        "normalized.audit_status = filters.audit_status;",
        "normalized.managed_status = filters.managed_status;",
        "normalized.backup_status = filters.backup_status;",
    )

    for fragment in required_fragments:
        assert fragment in content
