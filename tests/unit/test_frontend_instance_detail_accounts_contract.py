"""实例详情账户表紧凑状态列契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_detail_accounts_grid_uses_aligned_column_copy_and_compact_indicators() -> None:
    content = _read_text("app/static/js/modules/views/instances/detail.js")

    required_fragments = (
        "function buildAccountsGridColumns() {",
        "const STATUS_COLUMN_WIDTH = '64px';",
        "name: '是否可用',",
        "name: '是否删除',",
        "name: '是否超管',",
        "formatter: (cell, row) => renderAccountLockedCell(cell, getRowMeta(row)),",
        "formatter: (cell) => renderAccountDeletedBadge(Boolean(cell)),",
        "formatter: (cell) => renderAccountSuperuserBadge(Boolean(cell)),",
        "function renderAccountCompactIndicator({ icon, tone = 'muted', title, ariaLabel }) {",
        "icon: 'fa-circle-check'",
        "title: '正常'",
        "icon: 'fa-lock'",
        "title: '已锁定'",
        "icon: 'fa-minus'",
        "title: '未删除'",
        "icon: 'fa-trash'",
        "title: '已删除'",
        "icon: 'fa-user-shield'",
        "title: '普通用户'",
        "title: '超管用户'",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "name: '锁定'," not in content
    assert "name: '超管'," not in content
    assert "name: '删除'," not in content


def test_instance_detail_accounts_grid_styles_define_compact_indicator_tokens() -> None:
    content = _read_text("app/static/css/pages/instances/detail.css")

    required_fragments = (
        '#instance-accounts-grid .gridjs-th[data-column-id="is_locked"],',
        '#instance-accounts-grid .gridjs-th[data-column-id="is_deleted"],',
        '#instance-accounts-grid .gridjs-th[data-column-id="is_superuser"],',
        ".ledger-compact-indicator {",
        ".ledger-compact-indicator--success {",
        ".ledger-compact-indicator--danger {",
        ".ledger-compact-indicator--warning {",
        ".ledger-compact-indicator--muted {",
        '#instance-accounts-grid td[data-column-id="is_locked"] .ledger-compact-indicator,',
        '#instance-accounts-grid td[data-column-id="is_deleted"] .ledger-compact-indicator,',
        '#instance-accounts-grid td[data-column-id="is_superuser"] .ledger-compact-indicator {',
    )

    for fragment in required_fragments:
        assert fragment in content
