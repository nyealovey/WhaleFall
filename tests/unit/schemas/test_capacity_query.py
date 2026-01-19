from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.exceptions import ValidationError
from app.schemas.capacity_query import (
    CapacityDatabasesAggregationsQuery,
    CapacityDatabasesSummaryQuery,
    CapacityInstancesAggregationsQuery,
)
from app.schemas.validation import validate_or_raise
from app.utils.time_utils import time_utils


@pytest.mark.unit
def test_capacity_databases_aggregations_query_parses_dates_and_clamps() -> None:
    query = validate_or_raise(
        CapacityDatabasesAggregationsQuery,
        {
            "start_date": "2026-01-01",
            "end_date": "2026-01-02",
            "database_name": "  foo  ",
            "page": 0,
            "limit": 999,
            "get_all": "true",
            "db_type": "   ",
            "period_type": "",
        },
    )
    filters = query.to_filters()

    assert filters.start_date == date(2026, 1, 1)
    assert filters.end_date == date(2026, 1, 2)
    assert filters.database_name == "foo"
    assert filters.page == 1
    assert filters.limit == 200
    assert filters.get_all is True
    assert filters.db_type is None
    assert filters.period_type is None


@pytest.mark.unit
def test_capacity_databases_summary_query_parses_ids() -> None:
    query = validate_or_raise(
        CapacityDatabasesSummaryQuery,
        {
            "instance_id": "123",
            "database_id": " 456 ",
        },
    )
    filters = query.to_filters()

    assert filters.instance_id == 123
    assert filters.database_id == 456


@pytest.mark.unit
def test_capacity_instances_aggregations_query_applies_time_range(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    monkeypatch.setattr(time_utils, "now_china", lambda: fixed_now)

    query = validate_or_raise(CapacityInstancesAggregationsQuery, {"time_range": "7"})
    filters = query.to_filters()

    assert filters.start_date == date(2026, 1, 3)
    assert filters.end_date == date(2026, 1, 10)


@pytest.mark.unit
def test_capacity_instances_aggregations_query_ignores_time_range_when_explicit_dates_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    monkeypatch.setattr(time_utils, "now_china", lambda: fixed_now)

    query = validate_or_raise(
        CapacityInstancesAggregationsQuery,
        {
            "time_range": "7",
            "start_date": "2026-01-01",
        },
    )
    filters = query.to_filters()

    assert filters.start_date == date(2026, 1, 1)
    assert filters.end_date is None


@pytest.mark.unit
def test_capacity_instances_aggregations_query_rejects_invalid_time_range() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(CapacityInstancesAggregationsQuery, {"time_range": "abc"})

    assert "time_range 必须为整数(天)" in str(excinfo.value)
