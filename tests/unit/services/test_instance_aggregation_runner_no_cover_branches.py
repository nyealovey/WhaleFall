from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.exc import SQLAlchemyError

import app.services.aggregation.instance_aggregation_runner as instance_aggregation_runner_module
from app.core.exceptions import DatabaseError
from app.services.aggregation.calculator import PeriodCalculator
from app.services.aggregation.instance_aggregation_runner import InstanceAggregationRunner, InstanceAggregationContext


@pytest.mark.unit
def test_invoke_callback_logs_warning_when_callback_raises(monkeypatch) -> None:
    runner = InstanceAggregationRunner(
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

    monkeypatch.setattr(instance_aggregation_runner_module, "log_warning", _fake_log_warning)
    runner._invoke_callback(_boom, object())

    assert any(msg == "聚合回调执行失败" for msg, _ in calls)


@pytest.mark.unit
def test_aggregate_period_logs_error_when_query_stats_raises(monkeypatch) -> None:
    runner = InstanceAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=lambda *_: None,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    instance = SimpleNamespace(id=1, name="inst-1")
    monkeypatch.setattr(instance_aggregation_runner_module.InstancesRepository, "list_active_instances", lambda: [instance])

    @contextmanager
    def _begin_nested():
        yield

    monkeypatch.setattr(instance_aggregation_runner_module.db.session, "begin_nested", _begin_nested)

    def _raise_query(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(runner, "_query_instance_stats", _raise_query)

    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        calls.append((message, dict(kwargs)))

    monkeypatch.setattr(instance_aggregation_runner_module, "log_error", _fake_log_error)

    result = runner.aggregate_period("daily", date(2026, 1, 1), date(2026, 1, 1))

    assert result["failed_instances"] == 1
    assert any(msg == "实例聚合计算失败" for msg, _ in calls)


@pytest.mark.unit
def test_persist_instance_aggregation_wraps_sqlalchemy_error(monkeypatch) -> None:
    runner = InstanceAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=lambda *_: None,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    context = InstanceAggregationContext(
        instance_id=1,
        instance_name="inst-1",
        period_type="daily",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )
    stats = [SimpleNamespace(collected_date=date(2026, 1, 1), total_size_mb=1, database_count=1)]

    monkeypatch.setattr(runner._repository, "get_existing_instance_aggregation", lambda **_kwargs: SimpleNamespace(id=None))

    def _raise_add(_obj: object) -> None:
        raise SQLAlchemyError("boom")

    monkeypatch.setattr(instance_aggregation_runner_module.db.session, "add", _raise_add)

    with pytest.raises(DatabaseError):
        runner._persist_instance_aggregation(context=context, stats=cast(Any, stats))


@pytest.mark.unit
def test_persist_instance_aggregation_wraps_unknown_commit_error(monkeypatch) -> None:
    def _commit_raises(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom")

    runner = InstanceAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=_commit_raises,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    context = InstanceAggregationContext(
        instance_id=1,
        instance_name="inst-1",
        period_type="daily",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )
    stats = [SimpleNamespace(collected_date=date(2026, 1, 1), total_size_mb=1, database_count=1)]

    monkeypatch.setattr(runner._repository, "get_existing_instance_aggregation", lambda **_kwargs: SimpleNamespace(id=1))
    monkeypatch.setattr(instance_aggregation_runner_module.db.session, "add", lambda *_: None)

    with pytest.raises(DatabaseError):
        runner._persist_instance_aggregation(context=context, stats=cast(Any, stats))


@pytest.mark.unit
def test_apply_change_statistics_sets_defaults_when_calculation_raises(monkeypatch) -> None:
    runner = InstanceAggregationRunner(
        ensure_partition_for_date=lambda *_: None,
        commit_with_partition_retry=lambda *_: None,
        period_calculator=PeriodCalculator(now_func=lambda: date(2026, 1, 1)),
        module="aggregation_test",
    )

    # make previous stats non-empty so it reaches the calculation branch
    prev_stats = [SimpleNamespace(collected_date=date(2025, 12, 31), total_size_mb=1, database_count=1)]
    monkeypatch.setattr(runner, "_query_instance_stats", lambda *_args, **_kwargs: prev_stats)

    calls: list[tuple[str, dict[str, object]]] = []

    def _fake_log_error(message: str, **kwargs: object) -> None:
        calls.append((message, dict(kwargs)))

    monkeypatch.setattr(instance_aggregation_runner_module, "log_error", _fake_log_error)

    class _DummyAggregation:
        avg_database_count = 1.0

        @property
        def total_size_mb(self) -> int:
            raise RuntimeError("boom")

    aggregation = cast(Any, _DummyAggregation())
    context = InstanceAggregationContext(
        instance_id=1,
        instance_name="inst-1",
        period_type="daily",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 1),
    )

    runner._apply_change_statistics(aggregation=aggregation, context=context)

    assert aggregation.growth_rate == 0
    assert aggregation.trend_direction == "stable"
    assert any(msg == "计算实例增量统计失败,使用默认值" for msg, _ in calls)
