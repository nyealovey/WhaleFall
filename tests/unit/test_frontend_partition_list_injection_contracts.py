from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_partition_list_must_not_construct_partition_service() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/admin/partitions/partition-list.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new PartitionService" not in content, "partition-list 组件不得自行 new PartitionService"
    assert "PartitionService" not in content, "partition-list 组件不得依赖全局 PartitionService"
    assert "gridUrl" in content, "partition-list 组件必须通过 gridUrl 注入数据源"


@pytest.mark.unit
def test_admin_partitions_page_must_inject_grid_url_to_partition_list() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/admin/partitions/index.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "PartitionsListGrid.mount" in content
    assert "gridUrl:" in content, "AdminPartitionsPage 必须为 partition-list 注入 gridUrl"

