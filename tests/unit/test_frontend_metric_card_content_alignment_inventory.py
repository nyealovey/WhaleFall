from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.unit
def test_frontend_dashboard_overview_metric_cards_match_inventory_copy() -> None:
    """DashboardOverviewPage 顶部 4 卡文案需与 inventory 对齐（避免口径/术语漂移）。"""

    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "app/templates/dashboard/overview.html"
    content = template.read_text(encoding="utf-8", errors="ignore")

    # 8=8-2: 标题不再写“（含已删除）”
    assert "账户总数（含已删除）" not in content
    assert "账户总数" in content

    # B3-u=B3-u-1: “总容量”卡不展示“xx% 使用率” meta（避免口径不清）。
    assert "% 使用率" not in content

    # B1: “数据库实例”卡 meta 需要展示在线/停用/已删除拆分。
    for label in ("在线", "停用", "已删除"):
        assert label in content, f"dashboard/overview.html 缺少实例拆分文案: {label}"


@pytest.mark.unit
def test_frontend_capacity_instances_metric_card_title_matches_inventory_copy() -> None:
    """InstanceAggregationsPage 顶部 4 卡文案需与 inventory 对齐。"""

    repo_root = Path(__file__).resolve().parents[2]
    template = repo_root / "app/templates/capacity/instances.html"
    content = template.read_text(encoding="utf-8", errors="ignore")

    # 4=4-1: “活跃实例数” -> “在线实例数”
    assert "活跃实例数" not in content
    assert "在线实例数" in content
