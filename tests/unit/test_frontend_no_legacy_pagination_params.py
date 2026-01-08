from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_table_query_params_pagination_contract_is_stable() -> None:
    """分页契约: 仅使用 `limit`，不解析 `page_size/pageSize`。"""
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "app/static/js/common/table-query-params.js"
    content = target.read_text(encoding="utf-8", errors="ignore")

    forbidden_markers = [
        'readValue(source, "pageSize")',
        'readValue(source, "page_size")',
        "pagination:legacy-page-size-param",
        "normalized.page_size =",
    ]
    hits = [marker for marker in forbidden_markers if marker in content]

    assert not hits, f"发现不期望的分页解析/输出残留: {hits}"
    assert 'readValue(source, "limit")' in content, "分页解析必须使用 limit"
    assert "normalized.limit = pageSize.value" in content, "分页 normalize 必须输出 limit"
    assert "delete normalized.page_size" in content, "分页 normalize 必须删除 page_size"
