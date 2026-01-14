"""AggregationTasksReadService period completeness tests."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.aggregation.aggregation_tasks_read_service import AggregationTasksReadService


@pytest.mark.unit
def test_has_aggregation_for_period_requires_all_active_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AggregationTasksReadService()

    monkeypatch.setattr(service, "count_active_instances", lambda: 2)
    monkeypatch.setattr(service._aggregation_repository, "has_aggregation_for_period", lambda **_: True)

    monkeypatch.setattr(
        service._aggregation_repository,
        "count_active_instances_with_database_size_aggregation",
        lambda **_: 1,
        raising=False,
    )
    monkeypatch.setattr(
        service._aggregation_repository,
        "count_active_instances_with_instance_size_aggregation",
        lambda **_: 1,
        raising=False,
    )

    assert service.has_aggregation_for_period(period_type="weekly", period_start=date(2026, 1, 5)) is False


@pytest.mark.unit
def test_has_aggregation_for_period_returns_true_when_fully_covered(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AggregationTasksReadService()

    def _unexpected(**_kwargs):  # noqa: ANN001
        raise AssertionError("legacy has_aggregation_for_period should not be called")

    monkeypatch.setattr(service._aggregation_repository, "has_aggregation_for_period", _unexpected)
    monkeypatch.setattr(service, "count_active_instances", lambda: 2)
    monkeypatch.setattr(
        service._aggregation_repository,
        "count_active_instances_with_database_size_aggregation",
        lambda **_: 2,
        raising=False,
    )
    monkeypatch.setattr(
        service._aggregation_repository,
        "count_active_instances_with_instance_size_aggregation",
        lambda **_: 2,
        raising=False,
    )

    assert service.has_aggregation_for_period(period_type="weekly", period_start=date(2026, 1, 5)) is True
