"""实例详情手动同步可用性契约测试."""

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def _read_text(relative_path: str) -> str:
    return (ROOT_DIR / relative_path).read_text(encoding="utf-8")


def test_instance_detail_manual_sync_no_longer_blocks_disabled_instances_in_frontend() -> None:
    content = _read_text("app/static/js/modules/views/instances/detail.js")

    forbidden_fragments = (
        "实例已停用，无法同步账户",
        "实例已停用，无法同步容量",
        "实例已停用，无法同步审计信息",
        "if (!isInstanceSyncAvailable()) {",
    )
    for fragment in forbidden_fragments:
        assert fragment not in content
