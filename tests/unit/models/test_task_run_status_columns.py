from __future__ import annotations

from typing import Any, cast

import pytest

from app.core.constants.status_types import TaskRunStatus
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem


@pytest.mark.unit
def test_task_run_status_columns_can_store_all_task_run_statuses() -> None:
    max_status_length = max(len(status) for status in TaskRunStatus.ALL)

    task_run_table = cast(Any, TaskRun).__table__
    task_run_item_table = cast(Any, TaskRunItem).__table__

    assert task_run_table.c.status.type.length >= max_status_length
    assert task_run_item_table.c.status.type.length >= max_status_length
