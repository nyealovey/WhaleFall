from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_capacity_data_source_component_must_not_construct_service() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/components/charts/data-source.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "new CapacityStatsService" not in content, (
        "capacity charts data-source 组件不得自行 new CapacityStatsService（必须由 Page Entry 注入）"
    )


@pytest.mark.unit
def test_capacity_manager_must_not_depend_on_global_data_source() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "app/static/js/modules/views/components/charts/manager.js"
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "CapacityStatsDataSource" not in content, (
        "CapacityStats.Manager 不得读取 window.CapacityStatsDataSource（必须通过构造参数注入）"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "relative_path",
    [
        "app/static/js/modules/views/capacity/databases.js",
        "app/static/js/modules/views/capacity/instances.js",
    ],
)
def test_capacity_pages_must_inject_data_source(relative_path: str) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / relative_path
    content = path.read_text(encoding="utf-8", errors="ignore")

    # new window.CapacityStats.Manager({ ..., dataSource: xxx })
    pattern = re.compile(
        r"new\s+window\.CapacityStats\.Manager\(\{[\s\S]*?\bdataSource\s*:",
        re.MULTILINE,
    )
    assert pattern.search(content), f"{relative_path}: CapacityStats.Manager 必须注入 dataSource"
