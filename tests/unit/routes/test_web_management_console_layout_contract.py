"""Web 管理页控制台布局契约测试.

目标:
- 标签管理页采用新的 management list page 结构
- 定时任务页采用新的 workbench/console 结构
- 账户分类页采用新的双栏工作台结构
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_web_tags_page_renders_management_console_layout(auth_client, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.routes.tags.manage._filter_options_service.list_tag_categories",
        lambda: [{"value": "ops", "label": "运维"}],
    )
    monkeypatch.setattr(
        "app.routes.tags.manage._tag_stats_service.get_stats",
        lambda: {"total": 12, "active": 9, "inactive": 3, "category_count": 4},
    )

    response = auth_client.get("/tags/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    required_fragments = (
        'class="tags-console"',
        "tags-command-deck",
        "tags-context-strip",
        "tags-filter-shell",
        "tags-grid-shell",
        "tags-grid-stage",
    )

    for fragment in required_fragments:
        assert fragment in html

    assert "tags-stats-grid" not in html


@pytest.mark.unit
def test_web_scheduler_page_renders_scheduler_console_layout(auth_client) -> None:
    response = auth_client.get("/scheduler/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    required_fragments = (
        'class="scheduler-console"',
        "scheduler-command-deck",
        "scheduler-summary-strip",
        "scheduler-stage",
        "scheduler-column",
        "scheduler-column__body",
    )

    for fragment in required_fragments:
        assert fragment in html


@pytest.mark.unit
def test_web_account_classification_page_renders_workbench_layout(auth_client) -> None:
    response = auth_client.get("/accounts/classifications/")
    assert response.status_code == 200

    html = response.get_data(as_text=True)
    required_fragments = (
        'class="classification-console"',
        "classification-command-deck",
        "classification-context-strip",
        "classification-workbench",
        "classification-rail",
        "classification-stage",
        "classification-rule-stage",
    )

    for fragment in required_fragments:
        assert fragment in html

    assert "classification-layout" not in html
