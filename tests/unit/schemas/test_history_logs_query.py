from datetime import datetime

import pytest

from app.core.exceptions import ValidationError
from app.schemas.history_logs_query import HistoryLogsListQuery, HistoryLogStatisticsQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_history_logs_list_query_defaults() -> None:
    query = validate_or_raise(HistoryLogsListQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 20
    assert filters.sort_field == "timestamp"
    assert filters.sort_order == "desc"
    assert filters.level is None
    assert filters.module is None
    assert filters.search_term == ""
    assert filters.start_time is None
    assert filters.end_time is None
    assert filters.hours is None


@pytest.mark.unit
def test_history_logs_list_query_normalizes() -> None:
    query = validate_or_raise(
        HistoryLogsListQuery,
        {
            "page": 1,
            "limit": 200,
            "sort": " TIMESTAMP ",
            "order": "ASC",
            "level": "error",
            "module": "  api  ",
            "search": "  foo  ",
            "start_time": "2026-01-01T00:00:00",
            "end_time": "2026-01-02T00:00:00",
            "hours": 24 * 90,
        },
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 200
    assert filters.sort_field == "timestamp"
    assert filters.sort_order == "asc"
    assert filters.module == "api"
    assert filters.search_term == "foo"
    assert isinstance(filters.start_time, datetime)
    assert isinstance(filters.end_time, datetime)
    assert filters.hours == 24 * 90


@pytest.mark.unit
def test_history_logs_list_query_rejects_invalid_sort_order() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(HistoryLogsListQuery, {"order": "weird"})


@pytest.mark.unit
def test_history_logs_list_query_rejects_out_of_range_hours() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(HistoryLogsListQuery, {"hours": 24 * 90 + 1})


@pytest.mark.unit
def test_history_log_statistics_query_defaults_to_24_hours() -> None:
    query = validate_or_raise(HistoryLogStatisticsQuery, {})
    assert query.hours == 24
