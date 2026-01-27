from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any, cast

import pytest

import app.services.aggregation.aggregation_service as aggregation_service_module
from app.core.exceptions import DatabaseError
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.results import AggregationStatus


@pytest.mark.unit
def test_commit_with_partition_retry_wraps_unknown_flush_error(monkeypatch) -> None:
    service = AggregationService()

    def _raise_flush() -> None:
        raise RuntimeError("boom")

    log_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        log_calls.append((message, dict(kwargs)))

    monkeypatch.setattr(aggregation_service_module.db.session, "flush", _raise_flush)
    monkeypatch.setattr(aggregation_service_module, "log_error", _fake_log_error)

    with pytest.raises(DatabaseError):
        service._commit_with_partition_retry(date(2026, 1, 1))

    assert any(msg == "提交聚合结果出现未知异常" for msg, _ in log_calls)


@pytest.mark.unit
def test_execute_instance_period_returns_failed_summary_when_executor_raises(monkeypatch) -> None:
    service = AggregationService()

    log_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        log_calls.append((message, dict(kwargs)))

    def _boom(*_args: object, **_kwargs: object) -> dict[str, Any]:
        raise RuntimeError("boom")

    instance = cast(Any, SimpleNamespace(id=1, name="inst-1"))
    monkeypatch.setattr(aggregation_service_module, "log_error", _fake_log_error)

    summary = service._execute_instance_period(instance, "daily", _boom)

    assert summary["status"] == AggregationStatus.FAILED.value
    assert any(msg == "实例周期聚合执行失败" for msg, _ in log_calls)


@pytest.mark.unit
def test_aggregate_database_periods_marks_failed_when_method_raises(monkeypatch) -> None:
    service = AggregationService()

    log_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        log_calls.append((message, dict(kwargs)))

    def _boom(**_kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(aggregation_service_module, "log_error", _fake_log_error)
    service._database_methods["daily"] = _boom  # type: ignore[assignment]

    result = service.aggregate_database_periods(["daily"])

    assert result["daily"]["status"] == AggregationStatus.FAILED.value
    assert any(msg == "数据库级聚合执行失败" for msg, _ in log_calls)
