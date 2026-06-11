"""详情页控制台模板契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_detail_page_uses_console_detail_shell() -> None:
    content = _read_text("app/templates/instances/detail.html")

    required_fragments = (
        "console-detail-page",
        "console-detail-hero",
        "console-detail-grid",
        "console-detail-main",
        "console-detail-rail",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_about_page_uses_console_detail_shell() -> None:
    content = _read_text("app/templates/about.html")

    required_fragments = (
        "console-detail-page",
        "console-detail-hero",
        "console-detail-grid",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_global_css_defines_console_detail_primitives() -> None:
    content = _read_text("app/static/css/global.css")

    required_fragments = (
        ".console-detail-page",
        ".console-detail-hero",
        ".console-detail-grid",
        ".console-detail-main",
        ".console-detail-rail",
    )

    for fragment in required_fragments:
        assert fragment in content
