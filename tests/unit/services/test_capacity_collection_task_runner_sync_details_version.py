from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import Any, cast

import pytest

from app.schemas.internal_contracts.sync_details_v1 import normalize_sync_details_v1
from app.services.capacity.capacity_collection_task_runner import CapacityCollectionTaskRunner


capacity_runner_module = importlib.import_module("app.services.capacity.capacity_collection_task_runner")


class _DummySyncSessionService:
    def __init__(self) -> None:
        self.complete_calls: list[dict[str, object]] = []

    def complete_instance_sync(self, record_id: int, *, stats: object, sync_details: dict[str, Any] | None = None) -> None:
        _ = (record_id, stats)
        normalize_sync_details_v1(sync_details)
        self.complete_calls.append({"record_id": record_id, "sync_details": sync_details})


class _DummyLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return None

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return None


class _DummyCollector:
    def synchronize_inventory(self) -> dict[str, object]:
        return {
            "refreshed": 1,
            "created": 0,
            "reactivated": 0,
            "deactivated": 0,
            "active_databases": ["db1"],
        }


@dataclass(slots=True)
class _DummyRecord:
    id: int


@dataclass(slots=True)
class _DummySession:
    session_id: str


@dataclass(slots=True)
class _DummyInstance:
    id: int
    name: str


@pytest.mark.unit
def test_capacity_runner_sync_inventory_adds_sync_details_version(monkeypatch) -> None:
    dummy_sync_session_service = _DummySyncSessionService()
    monkeypatch.setattr(capacity_runner_module, "sync_session_service", dummy_sync_session_service)

    payload, skipped = CapacityCollectionTaskRunner._sync_inventory_for_instance(
        collector=cast(Any, _DummyCollector()),
        record=cast(Any, _DummyRecord(id=1)),
        session=cast(Any, _DummySession(session_id="s1")),
        instance=cast(Any, _DummyInstance(id=1, name="inst-1")),
        logger=cast(Any, _DummyLogger()),
    )

    assert skipped is False
    assert payload.get("inventory")
    assert dummy_sync_session_service.complete_calls
    sync_details = cast(dict[str, Any], dummy_sync_session_service.complete_calls[0]["sync_details"])
    assert sync_details.get("version") == 1

