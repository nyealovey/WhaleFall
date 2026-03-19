"""账户/数据库台账 db type PNG 资源契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_accounts_ledgers_renderer_uses_png_db_type_assets() -> None:
    content = _read_text("app/static/js/modules/views/accounts/ledgers.js")

    required_fragments = (
        'const rawDbTypeMap = safeParseJSON(pageRoot.dataset.dbTypeMap || "{}", {});',
        "const dbTypeMetaMap = new Map(Object.entries(rawDbTypeMap));",
        'const assetUrl = meta?.asset_url || "";',
        'class="db-type-chip__asset"',
        'src="${escapeHtml(assetUrl)}"',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_databases_ledgers_renderer_uses_png_db_type_assets() -> None:
    content = _read_text("app/static/js/modules/views/databases/ledgers.js")

    required_fragments = (
        'const rawDbTypeMap = safeParseJSON(root.dataset.dbTypeMap || "{}", {});',
        "const dbTypeMetaMap = new Map(Object.entries(rawDbTypeMap));",
        'const assetUrl = meta?.asset_url || "";',
        'class="db-type-chip__asset"',
        'src="${escapeHtml(assetUrl)}"',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_db_type_asset_styles_are_shared_between_filters_and_badges() -> None:
    content = _read_text("app/static/css/components/chips.css")

    required_fragments = (
        ".db-type-chip__asset {",
        ".db-type-filter__asset {",
        "object-fit: contain;",
        "border-radius: 0.25rem;",
    )

    for fragment in required_fragments:
        assert fragment in content
