"""账户/数据库台账紧凑类型图标契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_accounts_ledgers_renderer_uses_compact_icon_only_type_column() -> None:
    content = _read_text("app/static/js/modules/views/accounts/ledgers.js")

    required_fragments = (
        'const TYPE_COLUMN_WIDTH = "64px";',
        'const STATUS_COLUMN_WIDTH = "64px";',
        'name: "是否可用",',
        'name: "是否删除",',
        'name: "是否超管",',
        'name: "类型",',
        'const rawDbTypeMap = safeParseJSON(pageRoot.dataset.dbTypeMap || "{}", {});',
        "const dbTypeMetaMap = new Map(Object.entries(rawDbTypeMap));",
        'formatter: (cell) => renderAvailabilityIndicator(Boolean(cell)),',
        'formatter: (cell) => renderDeletionIndicator(Boolean(cell)),',
        'formatter: (cell) => renderSuperuserIndicator(Boolean(cell)),',
        'const visual = LEDGER_DB_TYPE_VISUALS.get(normalized) || {};',
        'assetUrl: meta?.asset_url || "",',
        '<img class="ledger-compact-indicator__asset"',
        'src="${escapeHtml(assetUrl)}"',
    )

    for fragment in required_fragments:
        assert fragment in content

    assert 'name: "数据库类型"' not in content
    assert 'name: "可用性"' not in content
    assert 'name: "是否超级"' not in content
    assert 'name: "是否超极"' not in content


def test_databases_ledgers_renderer_uses_compact_icon_only_type_column() -> None:
    content = _read_text("app/static/js/modules/views/databases/ledgers.js")

    required_fragments = (
        'const TYPE_COLUMN_WIDTH = "64px";',
        'name: "类型",',
        'const rawDbTypeMap = safeParseJSON(root.dataset.dbTypeMap || "{}", {});',
        "const dbTypeMetaMap = new Map(Object.entries(rawDbTypeMap));",
        'const visual = LEDGER_DB_TYPE_VISUALS.get(normalized) || {};',
        'assetUrl: meta?.asset_url || "",',
        '<img class="ledger-compact-indicator__asset"',
        'src="${escapeHtml(assetUrl)}"',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_accounts_ledgers_renderer_uses_compact_icon_only_status_indicators() -> None:
    content = _read_text("app/static/js/modules/views/accounts/ledgers.js")

    required_fragments = (
        'function renderAvailabilityIndicator(isLocked) {',
        'icon: "fa-circle-check"',
        'title: "正常"',
        'icon: "fa-lock"',
        'title: "已锁定"',
        'function renderDeletionIndicator(isDeleted) {',
        'icon: "fa-minus"',
        'title: "未删除"',
        'icon: "fa-trash"',
        'title: "已删除"',
        'function renderSuperuserIndicator(isSuperuser) {',
        'icon: "fa-user-shield"',
        'title: "超管用户"',
        'title: "普通用户"',
        'return renderCompactIndicator({',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_ledger_compact_indicator_styles_are_defined_for_accounts_and_databases_pages() -> None:
    accounts_content = _read_text("app/static/css/pages/accounts/ledgers.css")
    databases_content = _read_text("app/static/css/pages/databases/ledgers.css")

    shared_fragments = (
        ".ledger-compact-indicator {",
        "width: 1.75rem;",
        "height: 1.75rem;",
        "border-radius: 0.75rem;",
        ".ledger-compact-indicator--primary {",
        ".ledger-compact-indicator--info {",
        ".ledger-compact-indicator--warning {",
        ".ledger-compact-indicator--danger {",
        ".ledger-compact-indicator--success {",
        ".ledger-compact-indicator--muted {",
        ".ledger-compact-indicator__asset {",
        "object-fit: contain;",
    )

    for fragment in shared_fragments:
        assert fragment in accounts_content
        assert fragment in databases_content

    account_layout_fragments = (
        '#accounts-grid td[data-column-id="db_type"] .ledger-compact-indicator,',
        '#accounts-grid td[data-column-id="is_locked"] .ledger-compact-indicator,',
        '#accounts-grid td[data-column-id="is_deleted"] .ledger-compact-indicator,',
        '#accounts-grid td[data-column-id="is_superuser"] .ledger-compact-indicator {',
    )
    for fragment in account_layout_fragments:
        assert fragment in accounts_content

    database_layout_fragments = (
        '#database-ledger-grid td[data-column-id="db_type"] .ledger-compact-indicator {',
    )
    for fragment in database_layout_fragments:
        assert fragment in databases_content
