"""标签选择器模态框契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_tag_selector_template_uses_three_pane_workspace() -> None:
    content = _read_text("app/templates/components/tag_selector.html")

    required_fragments = (
        "tag-selector__topbar",
        "tag-selector__workspace",
        "tag-selector__categories-pane",
        "tag-selector__results-pane",
        "tag-selector__selection-pane",
        'data-role="search-input"',
        'data-role="stats"',
        'data-role="selected-count"',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_tag_selector_view_and_controller_wire_search_and_selection_summary() -> None:
    view_content = _read_text("app/static/js/modules/views/components/tags/tag-selector-view.js")
    controller_content = _read_text("app/static/js/modules/views/components/tags/tag-selector-controller.js")

    view_fragments = (
        "searchInput:",
        "selectedCount:",
        "onSearchChange",
        'data-role="search-input"',
        "tag-selector__selected-item",
    )
    for fragment in view_fragments:
        assert fragment in view_content

    controller_fragments = (
        "onSearchChange:",
        "handleSearch(query)",
        "this.store.actions.setSearch(query);",
    )
    for fragment in controller_fragments:
        assert fragment in controller_content


def test_tag_selector_css_defines_modal_shell_and_three_pane_layout() -> None:
    content = _read_text("app/static/css/components/tag-selector.css")

    required_fragments = (
        ".tag-selector__topbar {",
        ".tag-selector__categories-pane {",
        ".tag-selector__results-pane {",
        ".tag-selector__selection-pane {",
        ".tag-selector__stats {",
        ".tag-selector__search {",
        ".tag-selector__selected-item {",
    )

    for fragment in required_fragments:
        assert fragment in content
