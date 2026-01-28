from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, cast

import pytest

from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1


accounts_tasks_module = importlib.import_module("app.tasks.accounts_sync_tasks")


class _DummyLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return None

    def exception(self, *_args: object, **_kwargs: object) -> None:
        return None


class _DummySyncSessionService:
    def __init__(self) -> None:
        self.complete_calls: list[dict[str, object]] = []
        self.fail_calls: list[dict[str, object]] = []

    def complete_instance_sync(self, record_id: int, *, stats: object, sync_details: dict[str, Any] | None = None) -> None:
        _ = (record_id, stats)
        normalize_sync_details_v1(sync_details)
        self.complete_calls.append({"record_id": record_id, "sync_details": sync_details})

    def fail_instance_sync(self, record_id: int, error_message: str, sync_details: dict[str, Any] | None = None) -> None:
        _ = (sync_details,)
        self.fail_calls.append({"record_id": record_id, "error_message": error_message})


class _DummyCoordinator:
    def __init__(self, _instance: object) -> None:
        return None

    def __enter__(self) -> "_DummyCoordinator":
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False

    def sync_all(self, *, session_id: str) -> dict[str, Any]:
        _ = session_id
        return {
            "inventory": {"created": 1, "deactivated": 0},
            "collection": {"updated": 0, "processed_records": 1},
        }


@dataclass(slots=True)
class _DummySession:
    session_id: str


@dataclass(slots=True)
class _DummyRecord:
    id: int


@dataclass(slots=True)
class _DummyInstance:
    id: int
    name: str


@pytest.mark.unit
def test_accounts_sync_task_single_instance_success_adds_sync_details_version(monkeypatch) -> None:
    dummy_sync_session_service = _DummySyncSessionService()
    monkeypatch.setattr(accounts_tasks_module, "sync_session_service", dummy_sync_session_service)
    monkeypatch.setattr(accounts_tasks_module, "AccountSyncCoordinator", _DummyCoordinator)

    result = accounts_tasks_module._sync_single_instance(
        session=cast(Any, _DummySession(session_id="s1")),
        record=cast(Any, _DummyRecord(id=1)),
        instance=cast(Any, _DummyInstance(id=1, name="inst-1")),
        sync_logger=cast(Any, _DummyLogger()),
    )

    assert result == (1, 0)
    assert dummy_sync_session_service.fail_calls == []
    assert dummy_sync_session_service.complete_calls
    sync_details = cast(dict[str, Any], dummy_sync_session_service.complete_calls[0]["sync_details"])
    assert sync_details.get("version") == 1

