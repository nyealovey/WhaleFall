from typing import Any, cast

import pytest

import app.services.scheduler.scheduler_job_write_service as scheduler_job_write_service_module
from app.services.scheduler.scheduler_job_write_service import SchedulerJobResource, SchedulerJobWriteService


class _DummyJob:
    id = "sync_accounts"
    name = "sync_accounts"


class _DummyScheduler:
    def __init__(self, job: object) -> None:
        self._job = job
        self.modified_job_id: object | None = None
        self.rescheduled_job_id: object | None = None
        self.rescheduled_trigger: object | None = None

    def modify_job(self, *_args: object, **_kwargs: object) -> None:
        self.modified_job_id = _args[0] if _args else None
        return

    def reschedule_job(self, job_id: object, **kwargs: object) -> object:
        self.rescheduled_job_id = job_id
        self.rescheduled_trigger = kwargs.get("trigger")
        return self._job

    def get_job(self, _job_id: object) -> object:
        return self._job


@pytest.mark.unit
def test_scheduler_job_write_service_upsert_uses_parse_payload(monkeypatch) -> None:
    service = SchedulerJobWriteService()
    job = _DummyJob()
    resource = SchedulerJobResource(scheduler=cast(Any, _DummyScheduler(job)), job=cast(Any, job))

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("parse_payload_called")

    monkeypatch.setattr(scheduler_job_write_service_module, "parse_payload", _raise, raising=False)

    with pytest.raises(RuntimeError, match="parse_payload_called"):
        service.upsert(
            {"trigger_type": "cron", "cron_expression": "*/5 * * * *"},
            resource=resource,
        )


@pytest.mark.unit
def test_scheduler_job_write_service_upsert_uses_validate_or_raise(monkeypatch) -> None:
    service = SchedulerJobWriteService()
    job = _DummyJob()
    resource = SchedulerJobResource(scheduler=cast(Any, _DummyScheduler(job)), job=cast(Any, job))

    def _passthrough(payload: object, **_kwargs: object) -> object:
        return payload

    def _raise(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("validate_or_raise_called")

    monkeypatch.setattr(scheduler_job_write_service_module, "parse_payload", _passthrough, raising=False)
    monkeypatch.setattr(scheduler_job_write_service_module, "validate_or_raise", _raise, raising=False)

    with pytest.raises(RuntimeError, match="validate_or_raise_called"):
        service.upsert(
            {"trigger_type": "cron", "cron_expression": "*/5 * * * *"},
            resource=resource,
        )


@pytest.mark.unit
def test_scheduler_job_write_service_reschedules_job_to_recalculate_next_run_time() -> None:
    service = SchedulerJobWriteService()
    job = _DummyJob()
    scheduler = _DummyScheduler(job)
    resource = SchedulerJobResource(scheduler=cast(Any, scheduler), job=cast(Any, job))

    service.upsert(
        {"trigger_type": "cron", "cron_expression": "*/5 * * * *"},
        resource=resource,
    )

    assert scheduler.rescheduled_job_id == "sync_accounts"
    assert scheduler.rescheduled_trigger is not None
    assert scheduler.modified_job_id is None
