from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_table_query_params_does_not_support_legacy_page_size_keys() -> None:
    """强下线: 不再兼容 `pageSize/limit` 等旧分页参数."""
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "app/static/js/common/table-query-params.js"
    content = target.read_text(encoding="utf-8", errors="ignore")

    legacy_markers = [
        'readValue(source, "pageSize")',
        'readValue(source, "limit")',
        "pagination:legacy-page-size-param",
    ]
    hits = [marker for marker in legacy_markers if marker in content]

    assert not hits, f"发现旧分页参数兼容残留: {hits}"
