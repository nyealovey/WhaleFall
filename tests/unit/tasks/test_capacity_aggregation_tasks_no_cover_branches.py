import pytest

from app.tasks import capacity_aggregation_tasks


class _StubLogger:
    def __init__(self) -> None:
        self.logged: list[tuple[str, dict[str, object]]] = []

    def exception(self, message: str, **kwargs: object) -> None:
        self.logged.append((message, dict(kwargs)))


class _StubRunner:
    def __init__(self) -> None:
        self.failed: list[tuple[int, str]] = []

    def fail_instance_sync(self, record_id: int, error_message: str) -> None:
        self.failed.append((record_id, error_message))


class _StubSession:
    def __init__(self) -> None:
        self.status: str | None = None
        self.completed_at = None


@pytest.mark.unit
def test_handle_aggregation_task_exception_suppresses_rollback_errors(monkeypatch) -> None:
    runner = _StubRunner()
    logger = _StubLogger()
    session = _StubSession()

    def _raise_rollback() -> None:
        raise RuntimeError("rollback boom")

    commits: list[bool] = []

    monkeypatch.setattr(capacity_aggregation_tasks.db.session, "rollback", _raise_rollback)
    monkeypatch.setattr(capacity_aggregation_tasks.db.session, "commit", lambda: commits.append(True))

    result = capacity_aggregation_tasks._handle_aggregation_task_exception(
        exc=ValueError("boom"),
        runner=runner,  # type: ignore[arg-type]
        sync_logger=logger,
        task_started_at=0.0,
        session=session,
        started_record_ids={1, 2},
        finalized_record_ids={2},
        selected_periods=["daily"],
    )

    assert result["status"] == capacity_aggregation_tasks.STATUS_FAILED
    assert result["periods_executed"] == ["daily"]
    assert session.status == "failed"
    assert commits
    assert runner.failed == [(1, "聚合任务异常: boom")]
