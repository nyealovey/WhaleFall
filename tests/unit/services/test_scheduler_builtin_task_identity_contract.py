from __future__ import annotations

import pytest

from app import scheduler
from app.core.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.schemas.yaml_configs import SchedulerTaskConfig


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

    assert {"email_alert", "calculate_database", "calculate_account", "sync_veeam_backups"} <= BUILTIN_TASK_IDS
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


@pytest.mark.unit
def test_scheduler_default_task_loading_adds_missing_tasks_without_replacing_existing(monkeypatch) -> None:
    class _ExistingJob:
        id = "sync_accounts"

    class _FakeScheduler:
        def __init__(self) -> None:
            self.added_job_ids: list[str] = []

        def get_jobs(self) -> list[_ExistingJob]:
            return [_ExistingJob()]

        def get_job(self, job_id: str) -> _ExistingJob | None:
            return _ExistingJob() if job_id == "sync_accounts" else None

        def add_job(self, _func, _trigger, **kwargs) -> None:
            self.added_job_ids.append(str(kwargs["id"]))

    fake_scheduler = _FakeScheduler()
    task_configs = [
        SchedulerTaskConfig(
            id="sync_accounts",
            name="账户同步",
            function="sync_accounts",
            trigger_type="cron",
            trigger_params={"second": 0, "minute": 0, "hour": 1},
        ),
        SchedulerTaskConfig(
            id="sync_veeam_backups",
            name="同步 Veeam 备份",
            function="sync_veeam_backups",
            trigger_type="cron",
            trigger_params={"second": 0, "minute": 0, "hour": 5},
        ),
    ]

    monkeypatch.setattr(scheduler, "scheduler", fake_scheduler)
    monkeypatch.setattr(scheduler, "_read_default_task_configs", lambda: task_configs)
    monkeypatch.setattr(scheduler, "_load_task_callable", lambda _function_name: lambda: None)

    scheduler._load_tasks_from_config(force=False)

    assert fake_scheduler.added_job_ids == ["sync_veeam_backups"]
