from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.services.cache_service as cache_service_module
import app.services.cache.cache_actions_service as cache_actions_service_module
import app.utils.rate_limiter as rate_limiter_module
from app.repositories.instances_repository import InstancesRepository
from app.services.cache.cache_actions_service import CacheActionsService
from app.services.cache_service import CacheService


@pytest.mark.unit
def test_rate_limiter_cache_failure_logs_fallback(monkeypatch) -> None:
    class _DummyLogger:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        def warning(self, event: str, **kwargs: object) -> None:
            self.calls.append((event, dict(kwargs)))

    dummy_logger = _DummyLogger()
    monkeypatch.setattr(rate_limiter_module, "get_system_logger", lambda: dummy_logger)

    class _DummyCache:
        @staticmethod
        def get(_key: str):  # noqa: ANN001
            raise ConnectionError("boom")

    limiter = rate_limiter_module.RateLimiter(cache=_DummyCache())
    result = limiter.is_allowed("user-1", "login", limit=1, window=60)
    assert result.get("allowed") is True

    assert dummy_logger.calls
    _, payload = dummy_logger.calls[0]
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "rate_limiter_cache_check_failed"


@pytest.mark.unit
def test_cache_service_get_rule_evaluation_cache_failure_logs_fallback(monkeypatch) -> None:
    class _DummyLogger:
        def __init__(self) -> None:
            self.warnings: list[dict[str, object]] = []

        def warning(self, _event: str, **kwargs: object) -> None:
            self.warnings.append(dict(kwargs))

        def debug(self, _event: str, **_kwargs: object) -> None:  # noqa: D401
            return

        def info(self, _event: str, **_kwargs: object) -> None:  # noqa: D401
            return

    class _DummyCache:
        @staticmethod
        def get(_key: str):  # noqa: ANN001
            raise RuntimeError("boom")

    dummy_logger = _DummyLogger()
    monkeypatch.setattr(cache_service_module, "logger", dummy_logger)
    service = CacheService(cache=_DummyCache())
    assert service.get_rule_evaluation_cache(rule_id=1, account_id=2) is None

    assert dummy_logger.warnings
    payload = dummy_logger.warnings[0]
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "cache_get_rule_evaluation_failed"


@pytest.mark.unit
def test_cache_service_set_rule_evaluation_cache_failure_logs_fallback(monkeypatch) -> None:
    class _DummyLogger:
        def __init__(self) -> None:
            self.warnings: list[dict[str, object]] = []

        def warning(self, _event: str, **kwargs: object) -> None:
            self.warnings.append(dict(kwargs))

        def debug(self, _event: str, **_kwargs: object) -> None:
            return

    class _DummyCache:
        @staticmethod
        def set(_key: str, _value: object, *, timeout: int):  # noqa: ANN001
            raise RuntimeError("boom")

    dummy_logger = _DummyLogger()
    monkeypatch.setattr(cache_service_module, "logger", dummy_logger)
    service = CacheService(cache=_DummyCache())
    assert service.set_rule_evaluation_cache(rule_id=1, account_id=2, result=True) is False

    assert dummy_logger.warnings
    payload = dummy_logger.warnings[0]
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "cache_set_rule_evaluation_failed"


@pytest.mark.unit
def test_cache_service_set_rule_evaluation_cache_ttl_zero_is_preserved(monkeypatch) -> None:
    class _DummyLogger:
        def debug(self, _event: str, **_kwargs: object) -> None:
            return

        def warning(self, _event: str, **_kwargs: object) -> None:
            return

    class _DummyCache:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def set(self, _key: str, _value: object, *, timeout: int) -> None:  # noqa: ANN001
            self.calls.append(timeout)

    dummy_cache = _DummyCache()
    monkeypatch.setattr(cache_service_module, "logger", _DummyLogger())
    service = CacheService(cache=dummy_cache)

    assert service.set_rule_evaluation_cache(rule_id=1, account_id=2, result=True, ttl=0) is True
    assert dummy_cache.calls == [0]


@pytest.mark.unit
def test_cache_actions_clear_all_cache_logs_fallback_and_counts(monkeypatch) -> None:
    class _DummyManager:
        @staticmethod
        def invalidate_instance_cache(instance_id: int) -> bool:
            if instance_id == 1:
                return True
            if instance_id == 2:
                return False
            raise RuntimeError("boom")

    monkeypatch.setattr(CacheActionsService, "_require_cache_service", staticmethod(lambda: _DummyManager()))
    monkeypatch.setattr(
        InstancesRepository,
        "list_active_instances",
        lambda: [SimpleNamespace(id=1), SimpleNamespace(id=2), SimpleNamespace(id=3)],
    )

    fallback_calls: list[dict[str, object]] = []

    def _fake_log_fallback(  # type: ignore[no-untyped-def]
        level,  # noqa: ANN001
        event,  # noqa: ANN001
        *,
        module,  # noqa: ANN001
        action,  # noqa: ANN001
        fallback_reason,  # noqa: ANN001
        **options,  # noqa: ANN001
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
    monkeypatch.setattr(cache_actions_service_module, "log_info", lambda _msg, *, module="app", **kw: info_calls.append(kw))

    result = CacheActionsService().clear_all_cache(operator_id=10)
    assert result.cleared_count == 1

    assert len(fallback_calls) == 2
    assert {call["fallback_reason"] for call in fallback_calls} == {"cache_invalidate_failed"}

    assert info_calls
    summary = info_calls[-1]
    assert summary.get("failed_count") == 2
    assert summary.get("fallback_count") == 2


@pytest.mark.unit
def test_cache_actions_classification_stats_partial_failure_logs_fallback(monkeypatch) -> None:
    class _DummyManager:
        @staticmethod
        def get_cache_stats() -> dict[str, object]:
            return {"keys": 1}

        @staticmethod
        def get_classification_rules_by_db_type_cache(db_type: str):  # noqa: ANN001
            if db_type == "mysql":
                raise RuntimeError("boom")
            return [{"id": 1}]

    monkeypatch.setattr(CacheActionsService, "_require_cache_service", staticmethod(lambda: _DummyManager()))
    monkeypatch.setattr(cache_actions_service_module, "CLASSIFICATION_DB_TYPES", ("mysql", "postgresql"))

    fallback_calls: list[str] = []

    def _fake_log_fallback(  # type: ignore[no-untyped-def]
        _level,  # noqa: ANN001
        _event,  # noqa: ANN001
        *,
        fallback_reason,  # noqa: ANN001
        **_options,  # noqa: ANN001
    ) -> None:
        fallback_calls.append(str(fallback_reason))

    monkeypatch.setattr(cache_actions_service_module, "log_fallback", _fake_log_fallback)

    result = CacheActionsService().get_classification_cache_stats()
    assert result.cache_enabled is True
    assert result.db_type_stats["postgresql"]["rules_cached"] is True
    assert result.db_type_stats["mysql"]["rules_cached"] is False
    assert "cache_stats_failed" in fallback_calls

