from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_partitions_chart_must_not_fallback_to_direct_requests() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    path = (
        repo_root
        / "app/static/js/modules/views/admin/partitions/charts/partitions-chart.js"
    )
    content = path.read_text(encoding="utf-8", errors="ignore")

    assert "createPartitionStore" not in content, "partitions-chart 不得自行创建 store"
    assert "PartitionService" not in content, "partitions-chart 不得自行 new Service 或依赖全局 Service"
    assert "fetchCoreMetrics" not in content, "partitions-chart 不得直连 service.fetchCoreMetrics（必须走 store.actions）"

