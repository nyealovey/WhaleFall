"""Tags color removal frontend contracts."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_tags_modal_template_removes_legacy_color_inputs() -> None:
    content = _read_text("app/templates/tags/modals/tag-modals.html")

    forbidden_fragments = (
        'id="tagColor"',
        'name="color"',
        'id="tagColorPreview"',
        ">颜色<",
    )

    for fragment in forbidden_fragments:
        assert fragment not in content


def test_tags_page_scripts_remove_color_column_and_preview_logic() -> None:
    modal_content = _read_text("app/static/js/modules/views/tags/modals/tag-modals.js")
    index_content = _read_text("app/static/js/modules/views/tags/index.js")

    modal_forbidden = (
        "tagColor",
        "tagColorPreview",
        "updateColorPreview",
        "color:",
    )
    for fragment in modal_forbidden:
        assert fragment not in modal_content

    index_forbidden = (
        'name: "颜色"',
        'id: "color"',
        "renderColorChip",
        "color_name",
    )
    for fragment in index_forbidden:
        assert fragment not in index_content


def test_tags_page_css_drops_color_column_width_rules() -> None:
    content = _read_text("app/static/css/pages/tags/index.css")

    assert 'data-column-id="color"' not in content
