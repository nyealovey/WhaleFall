from __future__ import annotations

import pytest

from app.core.constants.filter_options import TASK_RUN_CATEGORIES, TASK_RUN_TRIGGER_SOURCES


@pytest.mark.unit
def test_task_run_filter_labels_use_alert_and_short_source_labels() -> None:
    trigger_labels = {item["value"]: item["label"] for item in TASK_RUN_TRIGGER_SOURCES}
    category_labels = {item["value"]: item["label"] for item in TASK_RUN_CATEGORIES}

    assert trigger_labels["scheduled"] == "定时"
    assert trigger_labels["manual"] == "手动"
    assert trigger_labels["api"] == "API"

    assert category_labels["notification"] == "告警"
    assert category_labels["cluster"] == "群集"


@pytest.mark.unit
def test_task_run_filter_labels_include_partial_completion_status() -> None:
    from app.core.constants.filter_options import STATUS_TASK_RUN_OPTIONS

    status_labels = {item["value"]: item["label"] for item in STATUS_TASK_RUN_OPTIONS}

    assert status_labels["completed_with_errors"] == "部分完成"
