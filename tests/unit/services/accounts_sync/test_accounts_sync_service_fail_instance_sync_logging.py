from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, cast

import pytest

from app.services.accounts_sync.accounts_sync_service import AccountSyncService

accounts_sync_service_module = importlib.import_module("app.services.accounts_sync.accounts_sync_service")


@dataclass(slots=True)
class _DummySession:
    session_id: str


@dataclass(slots=True)
class _DummyRecord:
    id: int


class _DummySyncSessionService:
    def create_session(self, *, sync_type: str, sync_category: str, created_by: int | None) -> _DummySession:
        _ = (sync_type, sync_category, created_by)
        return _DummySession(session_id="session-1")

    def add_instance_records(self, session_id: str, instance_ids: list[int]) -> list[_DummyRecord]:
        _ = (session_id, instance_ids)
        return [_DummyRecord(id=1)]

    def start_instance_sync(self, record_id: int) -> None:
        _ = record_id
        # no-op

    def fail_instance_sync(self, record_id: int, *_args: object, **_kwargs: object) -> None:
        _ = record_id
        raise RuntimeError("fail_instance_sync_failed")


class _DummyLogger:
    def __init__(self) -> None:
        self.exception_calls: list[tuple[str, dict[str, object]]] = []

    def exception(self, event: str, **kwargs: object) -> None:
        self.exception_calls.append((event, dict(kwargs)))


@pytest.mark.unit
def test_sync_with_session_logs_when_fail_instance_sync_raises(monkeypatch) -> None:
    service = AccountSyncService()
    logger = _DummyLogger()
    cast(Any, service).sync_logger = logger

    dummy_sync_session_service = _DummySyncSessionService()
    monkeypatch.setattr(accounts_sync_service_module, "sync_session_service", dummy_sync_session_service)

    def _raise_sync(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("sync_failed")

    monkeypatch.setattr(service, "_sync_with_existing_session", _raise_sync)
    monkeypatch.setattr(service, "_emit_completion_log", lambda *_args, **_kwargs: None)

    class _DummyInstance:
        id = 1
        name = "inst-1"
        db_type = "mysql"

    instance = cast(Any, _DummyInstance())

    result = service._sync_with_session(instance, "manual_batch", created_by=None)

    assert result.get("success") is False

    events = [event for event, _ in logger.exception_calls]
    assert "标记实例同步失败时出错" in events
    assert "会话同步失败" in events
