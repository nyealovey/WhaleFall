"""实例详情数据库版本区块排版契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_detail_version_snippet_uses_secondary_small_left_aligned_copy() -> None:
    content = _read_text("app/static/css/pages/instances/detail.css")

    required_fragments = (
        ".basic-info-card__version-card {",
        "gap: 0.6rem;",
        ".instance-version-snippet {",
        "padding: 0.65rem 0.75rem;",
        "text-align: left;",
        ".instance-version-snippet code {",
        "font-size: 0.74rem;",
        "line-height: 1.45;",
        "text-align: left;",
    )

    for fragment in required_fragments:
        assert fragment in content
