from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

import app.repositories.scheduler_jobs_repository as scheduler_jobs_repository_module
from app.core.constants.sync_constants import SyncOperationType
from app.repositories.scheduler_jobs_repository import SchedulerJobsRepository


@dataclass(frozen=True)
class _DummySession:
    sync_type: str
    completed_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    created_at: datetime | None = None


@pytest.mark.unit
def test_resolve_session_last_run_uses_completed_at_only(monkeypatch: pytest.MonkeyPatch) -> None:
    ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    sessions = [
        _DummySession(
            sync_type=SyncOperationType.SCHEDULED_TASK.value,
            completed_at=None,
            updated_at=ts,
        ),
        _DummySession(
            sync_type=SyncOperationType.MANUAL_TASK.value,
            completed_at=None,
            created_at=ts,
        ),
    ]

    def _get_sessions_by_category(_category: str, limit: int = 50) -> list[_DummySession]:
        del _category, limit
        return sessions

    monkeypatch.setattr(
        scheduler_jobs_repository_module.SyncSession,
        "get_sessions_by_category",
        _get_sessions_by_category,
    )

    assert SchedulerJobsRepository.resolve_session_last_run(category="account", limit=10) is None


@pytest.mark.unit
def test_resolve_session_last_run_prefers_scheduled_completed_at(monkeypatch: pytest.MonkeyPatch) -> None:
    manual_ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    scheduled_ts = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)
    sessions = [
        _DummySession(sync_type=SyncOperationType.MANUAL_TASK.value, completed_at=manual_ts),
        _DummySession(sync_type=SyncOperationType.SCHEDULED_TASK.value, completed_at=scheduled_ts),
    ]

    def _get_sessions_by_category(_category: str, limit: int = 50) -> list[_DummySession]:
        del _category, limit
        return sessions

    monkeypatch.setattr(
        scheduler_jobs_repository_module.SyncSession,
        "get_sessions_by_category",
        _get_sessions_by_category,
    )

    assert (
        SchedulerJobsRepository.resolve_session_last_run(category="account", limit=10) == scheduled_ts.isoformat()
    )
