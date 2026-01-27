from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

from app.services.aggregation.capacity_aggregation_task_runner import CapacityAggregationTaskRunner, STATUS_FAILED


class _DummyLogger:
    def __init__(self) -> None:
        self.exception_calls: list[str] = []

    def exception(self, event: str, **_kwargs: object) -> None:
        self.exception_calls.append(event)


@pytest.mark.unit
def test_calculate_instance_aggregation_logs_when_service_raises(monkeypatch) -> None:
    runner = CapacityAggregationTaskRunner()
    logger = _DummyLogger()

    class _DummyService:
        def calculate_instance_aggregations(self, *_args: object, **_kwargs: object) -> object:
            raise RuntimeError("boom")

    captured: dict[str, object] = {}

    def _normalize_period_results(
        _instance: object,
        _selected_periods: object,
        period_results: dict[str, Any],
        _logger: object,
    ) -> tuple[dict[str, Any], list[str], int]:
        captured["period_results"] = period_results
        return period_results, ["err"], 0

    monkeypatch.setattr(runner, "_normalize_period_results", _normalize_period_results)

    instance = SimpleNamespace(id=1, name="inst-1")
    details, success, _count = runner.calculate_instance_aggregation(
        service=cast(Any, _DummyService()),
        instance=cast(Any, instance),
        selected_periods=["daily"],
        logger=cast(Any, logger),
    )

    assert success is False
    assert details["periods"]["daily"]["status"] == STATUS_FAILED
    assert "实例聚合执行异常" in logger.exception_calls
