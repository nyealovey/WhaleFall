from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from typing import Any

import pytest

from app.tasks import capacity_collection_tasks


class _StubLogger:
    def __init__(self) -> None:
        self.exceptions: list[tuple[str, dict[str, object]]] = []

    def info(self, *_: object, **__: object) -> None:
        return None

    def warning(self, *_: object, **__: object) -> None:
        return None

    def exception(self, message: str, **kwargs: object) -> None:
        self.exceptions.append((message, dict(kwargs)))


class _StubApp:
    def app_context(self):
        return nullcontext()


@pytest.mark.unit
def test_process_instance_with_fallback_rolls_back_and_marks_failed(monkeypatch) -> None:
    runner: Any = SimpleNamespace()
    runner.start_instance_sync_calls = []
    runner.fail_instance_sync_calls = []

    def _start(record_id: int) -> None:
        runner.start_instance_sync_calls.append(record_id)

    def _fail(record_id: int, message: str) -> None:
        runner.fail_instance_sync_calls.append((record_id, message))

    def _raise(*_: object, **__: object) -> None:
        raise RuntimeError("boom")

    runner.start_instance_sync = _start
    runner.process_capacity_instance = _raise
    runner.fail_instance_sync = _fail

    commits: list[bool] = []
    rollbacks: list[bool] = []

    monkeypatch.setattr(capacity_collection_tasks.db.session, "commit", lambda: commits.append(True))
    monkeypatch.setattr(capacity_collection_tasks.db.session, "rollback", lambda: rollbacks.append(True))

    fallback_calls: list[tuple[str, str, dict[str, object]]] = []

    def _log_fallback(level: str, event: str, **kwargs: object) -> None:
        fallback_calls.append((level, event, dict(kwargs)))

    monkeypatch.setattr(capacity_collection_tasks, "log_fallback", _log_fallback)

    session_obj = SimpleNamespace(session_id="s1")
    record = SimpleNamespace(id=10)
    instance = SimpleNamespace(id=7, name="i1")
    logger = _StubLogger()

    payload, totals = capacity_collection_tasks._process_instance_with_fallback(
        runner=runner,
        session_obj=session_obj,
        record=record,
        instance=instance,
        sync_logger=logger,
    )

    assert runner.start_instance_sync_calls == [10]
    assert rollbacks == [True]
    assert runner.fail_instance_sync_calls == [(10, "实例同步异常: boom")]
    assert commits

    assert payload["success"] is False
    assert payload["instance_id"] == 7
    assert payload["instance_name"] == "i1"
    assert payload["error"] == "boom"
    assert totals.total_failed == 1

    assert fallback_calls
    level, event, fields = fallback_calls[0]
    assert level == "exception"
    assert event == "实例同步异常(未分类)"
    assert fields.get("fallback_reason") == "capacity_instance_sync_failed"
    assert isinstance(fields.get("exception"), RuntimeError)


@pytest.mark.unit
def test_sync_databases_unclassified_exception_finalizes_run(monkeypatch) -> None:
    app = _StubApp()
    logger = _StubLogger()

    monkeypatch.setattr(capacity_collection_tasks, "create_app", lambda **_: app)
    monkeypatch.setattr(capacity_collection_tasks, "get_sync_logger", lambda: logger)

    class _StubRunner:
        def list_active_instances(self) -> list[object]:
            raise AttributeError("boom")

    monkeypatch.setattr(capacity_collection_tasks, "CapacityCollectionTaskRunner", lambda: _StubRunner())

    class _StubTaskRunsService:
        def __init__(self) -> None:
            self.failed: list[tuple[str, str]] = []

        def resolve_or_start_run(self, **_: object) -> str:
            return "run-1"

        def is_cancelled(self, run_id: str) -> bool:
            _ = run_id
            return False

        def mark_run_failed(self, run_id: str, *, error_message: str, **_: object) -> None:
            self.failed.append((run_id, error_message))

    task_runs_service = _StubTaskRunsService()
    monkeypatch.setattr(capacity_collection_tasks, "TaskRunsWriteService", lambda: task_runs_service)

    commits: list[bool] = []
    rollbacks: list[bool] = []

    monkeypatch.setattr(capacity_collection_tasks.db.session, "commit", lambda: commits.append(True))
    monkeypatch.setattr(capacity_collection_tasks.db.session, "rollback", lambda: rollbacks.append(True))

    result = capacity_collection_tasks.sync_databases(manual_run=True)

    assert result["success"] is False
    assert rollbacks
    assert task_runs_service.failed == [("run-1", "boom")]
    assert logger.exceptions
