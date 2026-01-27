from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from typing import cast

import pytest

import app.services.scheduler.scheduler_actions_service as scheduler_actions_service_module
from app.services.scheduler.scheduler_actions_service import SchedulerActionsService


@pytest.mark.unit
def test_run_job_in_background_logs_when_job_func_raises(monkeypatch) -> None:
    calls: list[tuple[str, str, dict[str, object]]] = []

    def _fake_log_with_context(level: str, message: str, **kwargs: object) -> None:
        calls.append((level, message, dict(kwargs)))

    class _DummyThread:
        def __init__(self, *, target: Callable[..., None], name: str, daemon: bool) -> None:
            self._target = target
            self.name = name
            self.daemon = daemon

        def start(self) -> None:
            self._target()

    class _DummyApp:
        @contextmanager
        def app_context(self):
            yield

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    class _DummyJob:
        def __init__(self) -> None:
            self.func = _boom
            self.args = ()
            self.kwargs = {}
            self.name = "dummy"

    class _DummyScheduler:
        running = True

        def get_job(self, job_id: str):
            _ = job_id
            return _DummyJob()

    monkeypatch.setattr(scheduler_actions_service_module, "log_with_context", _fake_log_with_context)
    monkeypatch.setattr(scheduler_actions_service_module.threading, "Thread", _DummyThread)
    monkeypatch.setattr(scheduler_actions_service_module, "has_app_context", lambda: True)
    monkeypatch.setattr(scheduler_actions_service_module, "current_app", _DummyApp())
    monkeypatch.setattr(scheduler_actions_service_module.scheduler_module, "get_scheduler", lambda: _DummyScheduler())

    service = SchedulerActionsService()
    thread_name = service.run_job_in_background(job_id="job-1", created_by=1)

    assert thread_name == "job-1_manual"
    assert calls

    level, message, kwargs = calls[0]
    assert level == "error"
    assert message == "任务函数执行失败"
    assert kwargs["module"] == "scheduler"
    assert kwargs["action"] == "run_job_background"
    context = cast(dict[str, object], kwargs["context"])
    extra = cast(dict[str, object], kwargs["extra"])
    assert context["job_id"] == "job-1"
    assert extra["error_type"] == "RuntimeError"
    assert extra["error_message"] == "boom"
