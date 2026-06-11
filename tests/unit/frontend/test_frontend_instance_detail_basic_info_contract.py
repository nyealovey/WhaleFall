"""实例详情基本信息资料卡契约测试."""

import re
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def _css_block(content: str, selector: str) -> str:
    pattern = re.compile(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", re.S)
    match = pattern.search(content)
    assert match is not None, f"缺少 {selector} CSS 块"
    return match.group("body")


def test_instance_detail_basic_info_uses_dossier_layout() -> None:
    content = _read_text("app/templates/instances/detail.html")

    required_fragments = (
        "basic-info-card__masthead",
        "basic-info-card__title-row",
        "basic-info-card__identity-strip",
        "basic-info-card__detail-grid",
        "basic-info-card__meta-row",
        "basic-info-card__version-card",
        "basic-info-card__tags-card",
        "basic-info-card__description-panel",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "运行记录" not in content
    assert "basic-info-card__time-card" not in content


def test_instance_detail_basic_info_preserves_runtime_hooks() -> None:
    content = _read_text("app/templates/instances/detail.html")

    required_fragments = (
        'class="basic-info-card__title',
        "chip-outline chip-outline--brand",
        "instance-version-snippet",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_instance_detail_css_defines_dossier_visual_language() -> None:
    content = _read_text("app/static/css/pages/instances/detail.css")

    required_fragments = (
        ".basic-info-card__masthead {",
        ".basic-info-card__title-row {",
        ".basic-info-card__identity-strip {",
        ".basic-info-card__detail-grid {",
        ".basic-info-card__meta-row {",
        ".basic-info-card__description-panel {",
    )

    for fragment in required_fragments:
        assert fragment in content


def test_instance_detail_version_snippet_uses_plain_white_and_no_forced_full_height() -> None:
    content = _read_text("app/static/css/pages/instances/detail.css")
    snippet_block = _css_block(content, ".instance-version-snippet")

    assert ".instance-version-snippet {" in content
    assert "background: #fff;" in snippet_block
    assert "min-height: 100%;" not in snippet_block
    assert "linear-gradient(145deg, rgba(255, 255, 255, 0.86), rgba(241, 237, 230, 0.82));" not in snippet_block
