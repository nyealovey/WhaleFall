from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_metric_card_contract_is_present() -> None:
    """指标卡组件契约: 组件文件存在 + base 引入 css + 模板/css 含基准 class."""
    repo_root = Path(__file__).resolve().parents[2]

    template_path = repo_root / "app/templates/components/ui/metric_card.html"
    css_path = repo_root / "app/static/css/components/metric-card.css"
    macros_path = repo_root / "app/templates/components/ui/macros.html"
    base_path = repo_root / "app/templates/base.html"

    assert template_path.exists(), "MetricCard 模板缺失: app/templates/components/ui/metric_card.html"
    assert css_path.exists(), "MetricCard CSS 缺失: app/static/css/components/metric-card.css"

    base_content = base_path.read_text(encoding="utf-8", errors="ignore")
    assert "css/components/metric-card.css" in base_content, "base.html 必须引入 MetricCard CSS"

    macros_content = macros_path.read_text(encoding="utf-8", errors="ignore")
    assert "metric_card" in macros_content, "macros.html 必须暴露 metric_card macro"

    template_content = template_path.read_text(encoding="utf-8", errors="ignore")
    css_content = css_path.read_text(encoding="utf-8", errors="ignore")

    assert "wf-metric-card" in template_content, "MetricCard 模板必须包含 wf-metric-card 基准 class"
    assert ".wf-metric-card" in css_content, "MetricCard CSS 必须定义 .wf-metric-card 样式"

