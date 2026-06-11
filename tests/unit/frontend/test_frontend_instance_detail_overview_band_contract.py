"""实例详情双标签概览带契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_detail_tabs_use_overview_band_structure() -> None:
    content = _read_text("app/templates/instances/detail.html")

    required_fragments = (
        "instance-overview-band",
        "instance-overview-band__facts",
        "instance-overview-band__controls",
        "instance-overview-band__realtime",
        "instance-data-pane__stack",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "instance-overview-band__hero" not in content
    assert "Capacity Register" not in content
    assert "Account Register" not in content


def test_instance_detail_overview_band_preserves_summary_ids() -> None:
    content = _read_text("app/templates/instances/detail.html")

    required_ids = (
        'id="databaseTotalCount"',
        'id="databaseOnlineCount"',
        'id="databaseDeletedCount"',
        'id="databaseTotalCapacity"',
        'id="accountTotalCount"',
        'id="accountActiveCount"',
        'id="accountDeletedCount"',
        'id="accountSuperuserCount"',
        'id="showDeletedDatabases"',
        'id="databaseSearchInput"',
        'id="showDeletedAccounts"',
        'id="accountSearchInput"',
        'data-action="toggle-deleted-databases"',
        'data-action="toggle-deleted-accounts"',
        'data-auto-submit',
    )

    for fragment in required_ids:
        assert fragment in content


def test_instance_detail_css_defines_overview_band_visual_language() -> None:
    content = _read_text("app/static/css/pages/instances/detail.css")

    required_fragments = (
        ".instance-overview-band {",
        ".instance-overview-band__facts {",
        ".instance-overview-band__fact {",
        ".instance-overview-band__controls {",
        ".instance-overview-band__search {",
        ".instance-data-pane__stack {",
    )

    for fragment in required_fragments:
        assert fragment in content

    assert ".instance-overview-band__hero {" not in content
