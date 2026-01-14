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

    def modify_job(self, *_args: object, **_kwargs: object) -> None:
        return

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
