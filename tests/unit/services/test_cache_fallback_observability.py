from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest
from flask_caching import Cache

import app.services.cache.cache_actions_service as cache_actions_service_module
from app.repositories.instances_repository import InstancesRepository
from app.services.cache.cache_actions_service import CacheActionsService
from app.utils.cache_utils import CacheManager


@pytest.mark.unit
def test_cache_manager_get_failure_logs_fallback() -> None:
    class _DummyLogger:
        def __init__(self) -> None:
            self.warnings: list[dict[str, object]] = []

        def warning(self, _event: str, **kwargs: object) -> None:
            self.warnings.append(dict(kwargs))

    class _DummyCache:
        @staticmethod
        def get(_key: str):
            raise RuntimeError("boom")

    dummy_logger = _DummyLogger()
    manager = CacheManager(cache=cast(Cache, _DummyCache()))
    manager.system_logger = dummy_logger  # type: ignore[assignment]
    assert manager.get("k1") is None

    assert dummy_logger.warnings
    payload = dummy_logger.warnings[0]
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "cache_get_failed"


@pytest.mark.unit
def test_cache_manager_set_failure_logs_fallback() -> None:
    class _DummyLogger:
        def __init__(self) -> None:
            self.warnings: list[dict[str, object]] = []

        def warning(self, _event: str, **kwargs: object) -> None:
            self.warnings.append(dict(kwargs))

    class _DummyCache:
        @staticmethod
        def set(_key: str, _value: object, *, timeout: int):
            raise RuntimeError("boom")

    dummy_logger = _DummyLogger()
    manager = CacheManager(cache=cast(Cache, _DummyCache()))
    manager.system_logger = dummy_logger  # type: ignore[assignment]
    assert manager.set("k1", "v1") is False

    assert dummy_logger.warnings
    payload = dummy_logger.warnings[0]
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "cache_set_failed"


@pytest.mark.unit
def test_cache_manager_delete_failure_logs_fallback() -> None:
    class _DummyLogger:
        def __init__(self) -> None:
            self.warnings: list[dict[str, object]] = []

        def warning(self, _event: str, **kwargs: object) -> None:
            self.warnings.append(dict(kwargs))

    class _DummyCache:
        @staticmethod
        def delete(_key: str):
            raise RuntimeError("boom")

    manager = CacheManager(cache=cast(Cache, _DummyCache()))
    manager.system_logger = _DummyLogger()  # type: ignore[assignment]

    assert manager.delete("k1") is False

    dummy_logger = cast("_DummyLogger", manager.system_logger)
    assert dummy_logger.warnings
    payload = dummy_logger.warnings[0]
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "cache_delete_failed"
    assert payload.get("error_type") == "RuntimeError"


@pytest.mark.unit
def test_cache_manager_set_ttl_zero_is_preserved() -> None:
    class _DummyLogger:
        def debug(self, _event: str, **_kwargs: object) -> None:
            return

        def warning(self, _event: str, **_kwargs: object) -> None:
            return

    class _DummyCache:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def set(self, _key: str, _value: object, *, timeout: int) -> None:
            self.calls.append(timeout)

    dummy_cache = _DummyCache()
    manager = CacheManager(cache=cast(Cache, dummy_cache), default_timeout=123)
    manager.system_logger = _DummyLogger()  # type: ignore[assignment]

    assert manager.set("k1", "v1", timeout=0) is True
    assert dummy_cache.calls == [0]


@pytest.mark.unit
def test_cache_actions_clear_all_cache_logs_fallback_and_counts(monkeypatch) -> None:
    def _fake_invalidate_instance_cache(instance_id: int) -> bool:
        if instance_id == 1:
            return True
        if instance_id == 2:
            return False
        raise RuntimeError("boom")

    monkeypatch.setattr(
        CacheActionsService, "_invalidate_instance_cache", staticmethod(_fake_invalidate_instance_cache)
    )
    monkeypatch.setattr(
        InstancesRepository,
        "list_active_instances",
        lambda: [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)],
    )

    fallback_calls: list[dict[str, object]] = []

    def _fake_log_fallback(  # type: ignore[no-untyped-def]
        level,
        event,
        *,
        module,
        action,
        fallback_reason,
        **options,
    ) -> None:
        fallback_calls.append(
            {
                "level": level,
                "event": event,
                "module": module,
                "action": action,
                "fallback_reason": fallback_reason,
                "options": options,
            }
        )

    info_calls: list[dict[str, object]] = []
    monkeypatch.setattr(cache_actions_service_module, "log_fallback", _fake_log_fallback)
    monkeypatch.setattr(
        cache_actions_service_module, "log_info", lambda _msg, *, module="app", **kw: info_calls.append(kw)
    )

    result = CacheActionsService().clear_all_cache(operator_id=10)
    assert result.cleared_count == 1

    assert len(fallback_calls) == 2
    assert {call["fallback_reason"] for call in fallback_calls} == {"cache_invalidate_failed"}

    assert info_calls
    summary = info_calls[-1]
    assert summary.get("failed_count") == 2
    assert summary.get("fallback_count") == 2


@pytest.mark.unit
def test_cache_actions_classification_stats_are_derived_from_all_rules_cache(monkeypatch) -> None:
    class _DummyManager:
        def __init__(self) -> None:
            self.keys: list[str] = []

        def get_stats(self) -> dict[str, object]:
            return {"keys": 1}

        def get(self, key: str):
            self.keys.append(key)
            return {
                "rules": [
                    {"id": 1, "db_type": "mysql"},
                    {"id": 2, "db_type": "MYSQL"},
                    {"id": 3, "db_type": "postgresql"},
                ]
            }

    dummy = _DummyManager()
    monkeypatch.setattr(CacheActionsService, "_get_cache_manager", staticmethod(lambda: dummy))
    monkeypatch.setattr(cache_actions_service_module, "CLASSIFICATION_DB_TYPES", ("mysql", "postgresql"))

    result = CacheActionsService().get_classification_cache_stats()
    assert result.cache_enabled is True
    assert dummy.keys == ["classification_rules:all"]
    assert result.db_type_stats["mysql"]["rules_cached"] is True
    assert result.db_type_stats["mysql"]["rules_count"] == 2
    assert result.db_type_stats["postgresql"]["rules_count"] == 1
