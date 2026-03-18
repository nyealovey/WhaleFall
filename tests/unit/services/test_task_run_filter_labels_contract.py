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
