from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_tags_page_uses_metric_card() -> None:
    """标签管理页顶部统计卡必须迁移到 MetricCard，并同步更新 JS selector。"""
    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "app/templates/tags/index.html"
    js_path = repo_root / "app/static/js/modules/views/tags/index.js"

    template_content = template.read_text(encoding="utf-8", errors="ignore")
    assert "tags-stat-card" not in template_content, "tags/index.html 不应再使用 tags-stat-card"
    assert "metric_card(" in template_content, "tags/index.html 必须使用 metric_card 宏"

    js_content = js_path.read_text(encoding="utf-8", errors="ignore")
    assert ".tags-stat-card__value" not in js_content, "tags/index.js 不应再依赖 .tags-stat-card__value"
    assert "metric-value" in js_content, "tags/index.js 应使用 MetricCard 的 value selector"

