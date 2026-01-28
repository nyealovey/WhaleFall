import pytest

from app.core.exceptions import ValidationError
from app.schemas.history_sessions_query import HistorySessionsListFiltersQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_history_sessions_list_filters_query_defaults() -> None:
    query = validate_or_raise(HistorySessionsListFiltersQuery, {})
    filters = query.to_filters()

    assert filters.sync_type == ""
    assert filters.sync_category == ""
    assert filters.status == ""
    assert filters.page == 1
    assert filters.limit == 20
    assert filters.sort_field == "started_at"
    assert filters.sort_order == "desc"


@pytest.mark.unit
def test_history_sessions_list_filters_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        HistorySessionsListFiltersQuery,
        {
            "sync_type": "  full  ",
            "sync_category": "  permissions  ",
            "status": "  failed  ",
            "page": 1,
            "limit": 100,
            "sort": " STATUS ",
            "order": "ASC",
        },
    )
    filters = query.to_filters()

    assert filters.sync_type == "full"
    assert filters.sync_category == "permissions"
    assert filters.status == "failed"
    assert filters.page == 1
    assert filters.limit == 100
    # 说明: sort_field 不做 lower()，保持旧行为（交给 repository 自行降级到默认字段）
    assert filters.sort_field == "STATUS"
    assert filters.sort_order == "asc"


@pytest.mark.unit
def test_history_sessions_list_filters_query_fallbacks_invalid_sort_order_to_default() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(HistorySessionsListFiltersQuery, {"order": "weird"})


@pytest.mark.unit
def test_history_sessions_list_filters_query_defaults_sort_field_when_blank() -> None:
    query = validate_or_raise(HistorySessionsListFiltersQuery, {"sort": "   "})
    assert query.to_filters().sort_field == "started_at"
