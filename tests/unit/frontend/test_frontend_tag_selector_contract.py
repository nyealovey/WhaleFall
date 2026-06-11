"""Tag selector frontend contracts."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_tag_selector_view_normalizes_string_categories_before_rendering() -> None:
    content = _read_text("app/static/js/modules/views/components/tags/tag-selector-view.js")

    required_fragments = (
        'function normalizeCategoryItem(item)',
        'if (typeof item === "string")',
        'return { value: normalized, label: normalized };',
        'categories.map(normalizeCategoryItem).filter(Boolean)',
    )

    for fragment in required_fragments:
        assert fragment in content
