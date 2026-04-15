"""筛选卡宽度预设契约测试."""

from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


@pytest.mark.unit
def test_filter_macros_use_width_presets_and_drop_col_class() -> None:
    content = _read_text("app/templates/components/filters/macros.html")

    assert "width_preset" in content
    assert "col_class" not in content


@pytest.mark.unit
def test_filter_templates_switch_to_width_presets() -> None:
    template_paths = (
        "app/templates/accounts/ledgers.html",
        "app/templates/auth/list.html",
        "app/templates/capacity/databases.html",
        "app/templates/capacity/instances.html",
        "app/templates/credentials/list.html",
        "app/templates/databases/ledgers.html",
        "app/templates/history/account_change_logs/account-change-logs.html",
        "app/templates/history/logs/logs.html",
        "app/templates/history/sessions/sync-sessions.html",
        "app/templates/instances/list.html",
        "app/templates/tags/index.html",
    )

    for path in template_paths:
        content = _read_text(path)
        assert "width_preset=" in content, path
        assert "col_class=" not in content, path


@pytest.mark.unit
def test_instances_list_uses_nowrap_filter_layout_and_explicit_presets() -> None:
    content = _read_text("app/templates/instances/list.html")

    required_fragments = (
        "layout='nowrap-desktop'",
        "search_input(value=search, placeholder='搜索实例 / 主机', width_preset='lg')",
        "db_type_filter(database_type_options, db_type, width_preset='sm')",
        "status_active_filter(status_options, status, width_preset='sm')",
        "select_filter('审计', 'audit_status', 'audit_status', audit_status_options, audit_status, '全部审计', width_preset='sm', allow_empty=False)",
        "select_filter('托管', 'managed_status', 'managed_status', managed_status_options, managed_status, '全部托管', width_preset='sm', allow_empty=False)",
        "select_filter('备份', 'backup_status', 'backup_status', backup_status_options, backup_status, '全部备份', width_preset='sm', allow_empty=False)",
        "tag_selector_filter(tag_options, selected_tags, field_id='instance-tag-selector', width_preset='md')",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert content.index("select_filter('托管'") < content.index("select_filter('备份'")
    assert content.index("select_filter('备份'") < content.index("tag_selector_filter(tag_options")


@pytest.mark.unit
def test_filter_common_css_defines_width_presets_and_nowrap_layout() -> None:
    content = _read_text("app/static/css/components/filters/filter-common.css")

    required_fragments = (
        ".filter-form--wrap",
        ".filter-form--nowrap-desktop",
        ".filter-field--sm",
        ".filter-field--md",
        ".filter-field--lg",
        ".filter-field--xl",
        ".filter-actions--inline",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert '.filter-form .row > [class*="col-"]' not in content
