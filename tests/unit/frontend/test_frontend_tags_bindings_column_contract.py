"""标签管理关联列展示契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_tags_bindings_column_uses_instance_count_stack() -> None:
    content = _read_text("app/static/js/modules/views/tags/index.js")

    required_fragments = (
        'name: "关联"',
        'id: "bindings"',
        'function renderBindings(meta)',
        'class="instance-count-stack"',
        'const variant = instanceCount ? "info" : "muted";',
        'status-pill status-pill--${variant}',
    )

    for fragment in required_fragments:
        assert fragment in content


def test_tags_index_css_allocates_and_styles_bindings_column() -> None:
    content = _read_text("app/static/css/pages/tags/index.css")

    required_fragments = (
        '#tags-grid td[data-column-id="bindings"]',
        "min-width: 150px;",
        ".instance-count-stack {",
    )

    for fragment in required_fragments:
        assert fragment in content
