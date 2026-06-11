"""实例详情数据库容量回退渲染契约测试."""

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_detail_capacity_fallback_reuses_overview_band_fact_layout() -> None:
    content = _read_text("app/static/js/modules/views/instances/detail.js")

    required_fragments = (
        "instance-overview-band__facts",
        'id="databaseTotalCount"',
        'id="databaseOnlineCount"',
        'id="databaseDeletedCount"',
        'id="databaseTotalCapacity"',
    )

    for fragment in required_fragments:
        assert fragment in content

    assert "instance-stat-card" not in content
