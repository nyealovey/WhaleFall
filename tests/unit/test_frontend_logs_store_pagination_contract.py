from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_logs_store_pagination_contract_is_stable() -> None:
    """日志中心分页契约: 请求使用 page_size, 响应仅使用 limit."""
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "app/static/js/modules/stores/logs_store.js"
    content = target.read_text(encoding="utf-8", errors="ignore")

    legacy_markers = [
        "data.per_page",
        "data.perPage",
        "limit: state.pagination.perPage",
    ]
    hits = [marker for marker in legacy_markers if marker in content]
    assert not hits, f"发现日志分页兼容残留: {hits}"

    assert "page_size: state.pagination.perPage" in content, "日志分页请求必须使用 page_size 参数"

