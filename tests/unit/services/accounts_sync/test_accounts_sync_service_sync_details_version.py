from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, cast

import pytest

from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1
from app.services.accounts_sync.accounts_sync_service import AccountSyncService


accounts_sync_service_module = importlib.import_module("app.services.accounts_sync.accounts_sync_service")


@dataclass(slots=True)
class _DummySession:
    session_id: str


@dataclass(slots=True)
class _DummyRecord:
    id: int


class _DummySyncSessionService:
    def __init__(self) -> None:
        self.complete_calls: list[dict[str, object]] = []
        self.fail_calls: list[dict[str, object]] = []

    def create_session(self, *, sync_type: str, sync_category: str, created_by: int | None) -> _DummySession:
        _ = (sync_type, sync_category, created_by)
        return _DummySession(session_id="session-1")

    def add_instance_records(self, session_id: str, instance_ids: list[int]) -> list[_DummyRecord]:
        _ = (session_id, instance_ids)
        return [_DummyRecord(id=1)]

    def start_instance_sync(self, record_id: int) -> None:
        _ = record_id

    def complete_instance_sync(self, record_id: int, *, stats: object, sync_details: dict[str, Any] | None = None) -> None:
        _ = (record_id, stats)
        normalize_sync_details_v1(sync_details)
        self.complete_calls.append({"record_id": record_id, "sync_details": sync_details})

    def fail_instance_sync(self, record_id: int, *args: object, **kwargs: object) -> None:
        _ = (record_id, args)
        self.fail_calls.append({"record_id": record_id, **dict(kwargs)})


@pytest.mark.unit
def test_sync_with_session_success_adds_sync_details_version(monkeypatch) -> None:
    service = AccountSyncService()
    monkeypatch.setattr(service, "_emit_completion_log", lambda *_args, **_kwargs: None)

    dummy_sync_session_service = _DummySyncSessionService()
    monkeypatch.setattr(accounts_sync_service_module, "sync_session_service", dummy_sync_session_service)

    def _fake_sync_with_existing_session(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "success": True,
            "details": {
                "inventory": {"created": 1, "deactivated": 0},
                "collection": {"updated": 0, "processed_records": 1},
            },
        }

    monkeypatch.setattr(service, "_sync_with_existing_session", _fake_sync_with_existing_session)

    class _DummyInstance:
        id = 1
        name = "inst-1"
        db_type = "mysql"

    instance = cast(Any, _DummyInstance())
    result = service._sync_with_session(instance, "manual_batch", created_by=None)

    assert result.get("success") is True
    assert dummy_sync_session_service.fail_calls == []
    assert dummy_sync_session_service.complete_calls
    sync_details = cast(dict[str, Any], dummy_sync_session_service.complete_calls[0]["sync_details"])
    assert sync_details.get("version") == 1

