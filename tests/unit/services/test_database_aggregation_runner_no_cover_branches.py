from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from typing import Any, cast

import pytest

import app.services.aggregation.database_aggregation_runner as database_aggregation_runner_module
from app.services.aggregation.calculator import PeriodCalculator
from app.services.aggregation.database_aggregation_runner import DatabaseAggregationRunner


@pytest.mark.unit
def test_invoke_callback_logs_warning_when_callback_raises(monkeypatch) -> None:
    runner = DatabaseAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=lambda *_: None,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_warning(message: str, **kwargs: object) -> None:
        calls.append((message, dict(kwargs)))

    def _boom(*_args: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(database_aggregation_runner_module, "log_warning", _fake_log_warning)

    runner._invoke_callback(_boom, object())

    assert any(msg == "聚合回调执行失败" for msg, _ in calls)


@pytest.mark.unit
def test_aggregate_period_logs_error_when_instance_aggregation_raises(monkeypatch) -> None:
    runner = DatabaseAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=lambda *_: None,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    instance = SimpleNamespace(id=1, name="inst-1")
    monkeypatch.setattr(database_aggregation_runner_module.InstancesRepository, "list_active_instances", lambda: [instance])

    @contextmanager
    def _begin_nested():
        yield

    monkeypatch.setattr(database_aggregation_runner_module.db.session, "begin_nested", _begin_nested)

    def _raise_instance(**_kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(runner, "_aggregate_databases_for_instance", _raise_instance)

    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        calls.append((message, dict(kwargs)))

    monkeypatch.setattr(database_aggregation_runner_module, "log_error", _fake_log_error)

    result = runner.aggregate_period("daily", date(2026, 1, 1), date(2026, 1, 1))

    assert result["failed_instances"] == 1
    assert any(msg == "实例数据库聚合执行失败" for msg, _ in calls)


@pytest.mark.unit
def test_apply_change_statistics_sets_default_values_when_calculation_raises(monkeypatch) -> None:
    runner = DatabaseAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=lambda *_: None,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        calls.append((message, dict(kwargs)))

    monkeypatch.setattr(database_aggregation_runner_module, "log_error", _fake_log_error)

    class _DummyAggregation:
        avg_data_size_mb = None

        @property
        def avg_size_mb(self) -> int:
            raise RuntimeError("boom")

    aggregation = cast(Any, _DummyAggregation())
    runner._apply_change_statistics_from_previous(
        aggregation=aggregation,
        prev_avg_size_mb=1.0,
        prev_avg_data_size_mb=None,
    )

    assert aggregation.size_change_mb == 0
    assert aggregation.growth_rate == 0
    assert any(msg == "计算数据库增量统计失败,使用默认值" for msg, _ in calls)
