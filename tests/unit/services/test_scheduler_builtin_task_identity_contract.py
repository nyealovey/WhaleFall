from __future__ import annotations

import pytest

import app.scheduler as scheduler
from app.core.constants.scheduler_jobs import BUILTIN_TASK_IDS


@pytest.mark.unit
def test_scheduler_builtin_task_ids_and_functions_use_short_names() -> None:
    tasks = scheduler._read_default_task_configs()
    task_ids = {task.id for task in tasks}
    function_names = {task.function for task in tasks}

    assert "email_alert" in task_ids
    assert "calculate_database" in task_ids
    assert "calculate_account" in task_ids
    assert "sync_veeam_backups" in task_ids

    assert "email_alert" in function_names
    assert "calculate_database" in function_names
    assert "calculate_account" in function_names
    assert "sync_veeam_backups" in function_names

    assert "send_email_alert_digest" not in task_ids
    assert "calculate_database_aggregations" not in task_ids
    assert "calculate_account_classification" not in task_ids

    assert "send_email_alert_digest" not in function_names
    assert "calculate_database_aggregations" not in function_names
    assert "calculate_account_classification" not in function_names

    assert BUILTIN_TASK_IDS >= {"email_alert", "calculate_database", "calculate_account", "sync_veeam_backups"}
    assert "send_email_alert_digest" not in BUILTIN_TASK_IDS
    assert "calculate_database_aggregations" not in BUILTIN_TASK_IDS
    assert "calculate_account_classification" not in BUILTIN_TASK_IDS

    assert "email_alert" in scheduler.TASK_FUNCTIONS
    assert "calculate_database" in scheduler.TASK_FUNCTIONS
    assert "calculate_account" in scheduler.TASK_FUNCTIONS
    assert "sync_veeam_backups" in scheduler.TASK_FUNCTIONS

    assert "send_email_alert_digest" not in scheduler.TASK_FUNCTIONS
    assert "calculate_database_aggregations" not in scheduler.TASK_FUNCTIONS
    assert "calculate_account_classification" not in scheduler.TASK_FUNCTIONS
