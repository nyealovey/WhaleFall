from __future__ import annotations

import re
from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_table_query_params_pagination_contract_is_stable() -> None:
    """分页契约: 仅使用 `limit`，不解析 `page_size/pageSize`。"""
    repo_root = Path(__file__).resolve().parents[2]
    target = repo_root / "app/static/js/common/table-query-params.js"
    content = target.read_text(encoding="utf-8", errors="ignore")

    forbidden_patterns = [
        re.compile(r'readValue\s*\(\s*source\s*,\s*["\']pageSize["\']\s*\)'),
        re.compile(r'readValue\s*\(\s*source\s*,\s*["\']page_size["\']\s*\)'),
        re.compile(r"\bnormalized\.page_size\s*="),
        re.compile(r"\bnormalized\.pageSize\s*="),
        re.compile(r"pagination:legacy-page-size-param"),
    ]
    hits = [pattern.pattern for pattern in forbidden_patterns if pattern.search(content)]

    assert not hits, f"发现不期望的分页解析/输出残留: {hits}"

    assert re.search(r'readValue\s*\(\s*source\s*,\s*["\']limit["\']\s*\)', content), "分页解析必须使用 limit"
    assert re.search(r"\bnormalized\.limit\b", content), "分页 normalize 必须输出 limit"
    assert re.search(r"\bdelete\s+normalized\.page_size\b", content), "分页 normalize 必须删除 page_size"
    assert re.search(r"\bdelete\s+normalized\.pageSize\b", content), "分页 normalize 必须删除 pageSize"
