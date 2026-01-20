import pytest

from app.schemas.account_change_logs_query import AccountChangeLogsListQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_account_change_logs_list_query_defaults() -> None:
    query = validate_or_raise(AccountChangeLogsListQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 20
    assert filters.sort_field == "change_time"
    assert filters.sort_order == "desc"
    assert filters.search_term == ""
    assert filters.instance_id is None
    assert filters.db_type is None
    assert filters.change_type is None
    assert filters.status is None
    assert filters.hours is None


@pytest.mark.unit
def test_account_change_logs_list_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        AccountChangeLogsListQuery,
        {
            "page": 0,
            "limit": 999,
            "sort": " CHANGE_TIME ",
            "order": "ASC",
            "search": "  alice  ",
            "instance_id": " 42 ",
            "db_type": " MySQL ",
            "change_type": " MODIFY_PRIVILEGE ",
            "status": " SUCCESS ",
            "hours": 999999,
        },
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 200
    assert filters.sort_field == "change_time"
    assert filters.sort_order == "asc"
    assert filters.search_term == "alice"
    assert filters.instance_id == 42
    assert filters.db_type == "mysql"
    assert filters.change_type == "modify_privilege"
    assert filters.status == "success"
    assert filters.hours == 2160


@pytest.mark.unit
def test_account_change_logs_list_query_fallbacks_invalid_sort_order_to_default() -> None:
    query = validate_or_raise(AccountChangeLogsListQuery, {"order": "weird"})
    assert query.to_filters().sort_order == "desc"


@pytest.mark.unit
def test_account_change_logs_list_query_defaults_sort_field_when_blank() -> None:
    query = validate_or_raise(AccountChangeLogsListQuery, {"sort": "   "})
    assert query.to_filters().sort_field == "change_time"
