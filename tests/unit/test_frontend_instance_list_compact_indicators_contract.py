"""实例管理列表紧凑图标指示器契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_list_renderer_uses_icon_only_type_and_status_indicators() -> None:
    content = _read_text("app/static/js/modules/views/instances/list.js")

    required_fragments = (
        "const TYPE_COLUMN_WIDTH = '64px';",
        "const STATUS_COLUMN_WIDTH = '64px';",
        "const INSTANCE_DB_TYPE_VISUALS = new Map([",
        "['postgresql', { icon: 'fa-layer-group', tone: 'info' }],",
        "['oracle', { icon: 'fa-cube', tone: 'danger' }],",
        "return renderCompactIndicator({",
        "title: meta.display_name || typeStr || '未知类型'",
        "ariaLabel: `数据库类型 ${meta.display_name || typeStr || '未知类型'}`",
        "icon: 'fa-minus-circle'",
        "title: '禁用'",
        "ariaLabel: '实例状态 禁用'",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "renderDbTypeBadge(cell)" in content
    assert "renderStatusBadge(resolveRowMeta(row))" in content


def test_instance_list_css_defines_compact_indicator_tokens() -> None:
    content = _read_text("app/static/css/pages/instances/list.css")

    required_fragments = (
        ".instance-compact-indicator {",
        "width: 1.75rem;",
        "height: 1.75rem;",
        "border-radius: 0.75rem;",
        ".instance-compact-indicator--primary {",
        ".instance-compact-indicator--info {",
        ".instance-compact-indicator--warning {",
        ".instance-compact-indicator--danger {",
        ".instance-compact-indicator--success {",
        ".instance-compact-indicator--muted {",
        "#instances-grid td[data-column-id=\"db_type\"] .instance-compact-indicator,",
        "#instances-grid td[data-column-id=\"status\"] .instance-compact-indicator {",
    )

    for fragment in required_fragments:
        assert fragment in content
