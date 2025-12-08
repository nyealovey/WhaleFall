"""AggregationService 周期窗口相关单测."""

from __future__ import annotations

from datetime import date
from types import MethodType, SimpleNamespace

import pytest

from app.models.instance import Instance
from app.services.aggregation.aggregation_service import AggregationService
from app.services.aggregation.calculator import PeriodCalculator
from app.services.aggregation.results import AggregationStatus


class _DummyRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, date, date]] = []

    def aggregate_period(self, period_type, start_date, end_date, **_):
        self.calls.append((period_type, start_date, end_date))
        return {
            "status": AggregationStatus.COMPLETED.value,
            "processed_records": 0,
        }


@pytest.mark.unit
def test_aggregate_database_periods_uses_previous_daily(monkeypatch) -> None:
    """验证覆盖配置后,日聚合会使用上一日窗口."""
    calc = PeriodCalculator(now_func=lambda: date(2025, 12, 1))
    service = AggregationService(period_calculator=calc)
    dummy_runner = _DummyRunner()
    service.database_runner = dummy_runner  # type: ignore[assignment]

    result = service.aggregate_database_periods(
        ["daily"],
        use_current_periods={"daily": False},
    )

    assert result["daily"]["status"] == AggregationStatus.COMPLETED.value
    assert dummy_runner.calls, "应触发数据库聚合执行"
    _, start_date, end_date = dummy_runner.calls[0]
    assert start_date == date(2025, 11, 30)
    assert end_date == date(2025, 11, 30)


@pytest.mark.unit
def test_instance_aggregations_daily_override(monkeypatch) -> None:
    """calculate_instance_aggregations 接收覆盖配置后会向下游透传."""
    calc = PeriodCalculator(now_func=lambda: date(2025, 12, 1))
    service = AggregationService(period_calculator=calc)

    stub_instance = SimpleNamespace(id=1, name="demo", is_active=True)

    class _Query:
        def get(self, _instance_id):
            return stub_instance

    monkeypatch.setattr(Instance, "query", _Query())

    captured = {}

    def _fake_daily(self, instance_id, *, use_current_period=True):
        captured["instance_id"] = instance_id
        captured["use_current_period"] = use_current_period
        return {
            "status": AggregationStatus.COMPLETED.value,
            "period_type": "daily",
        }

    service.calculate_daily_aggregations_for_instance = MethodType(_fake_daily, service)

    summary = service.calculate_instance_aggregations(
        stub_instance.id,
        periods=["daily"],
        use_current_periods={"daily": False},
    )

    assert summary["status"] == AggregationStatus.COMPLETED.value
    assert captured["instance_id"] == stub_instance.id
    assert captured["use_current_period"] is False
