from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.tasks import email_alert_tasks


class _StubApp:
    def app_context(self):
        return nullcontext()


class _StubLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return None

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return None

    def exception(self, *_args: object, **_kwargs: object) -> None:
        return None


@pytest.mark.unit
def test_send_email_alert_digest_skips_when_no_pending_events(monkeypatch) -> None:
    monkeypatch.setattr(email_alert_tasks, "create_app", lambda **_: _StubApp())
    monkeypatch.setattr(email_alert_tasks, "get_system_logger", lambda: _StubLogger())

    class _StubDigestService:
        def send_pending_digest(self) -> dict[str, object]:
            return {
                "sent": False,
                "skipped": True,
                "skip_reason": "no_pending_events",
                "event_count": 0,
            }

    monkeypatch.setattr(email_alert_tasks, "EmailAlertDigestService", lambda: _StubDigestService())

    run = SimpleNamespace(status="running", error_message=None, completed_at=None, summary_json=None)

    class _StubQuery:
        def filter_by(self, **_: object):
            return self

        def first(self):
            return run

    monkeypatch.setattr(email_alert_tasks, "TaskRun", SimpleNamespace(query=_StubQuery()))

    class _StubTaskRunsWriteService:
        def __init__(self) -> None:
            self.finalized: list[str] = []

        def start_run(self, **_: object) -> str:
            return "run-1"

        def finalize_run(self, run_id: str) -> None:
            self.finalized.append(run_id)

    task_runs_service = _StubTaskRunsWriteService()
    monkeypatch.setattr(email_alert_tasks, "TaskRunsWriteService", lambda: task_runs_service)

    commits: list[bool] = []
    monkeypatch.setattr(email_alert_tasks.db.session, "commit", lambda: commits.append(True))
    monkeypatch.setattr(email_alert_tasks.db.session, "rollback", lambda: None)

    result = email_alert_tasks.send_email_alert_digest()

    assert result["success"] is True
    assert result["event_count"] == 0
    assert task_runs_service.finalized == ["run-1"]
    assert commits
