import pytest

from app.schemas.users_query import UserListFiltersQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_user_list_filters_query_defaults() -> None:
    query = validate_or_raise(UserListFiltersQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 10
    assert filters.search == ""
    assert filters.role is None
    assert filters.status is None
    assert filters.sort_field == "created_at"
    assert filters.sort_order == "desc"


@pytest.mark.unit
def test_user_list_filters_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        UserListFiltersQuery,
        {
            "page": 0,
            "limit": 999,
            "search": " foo ",
            "role": "admin",
            "status": "inactive",
            "sort": " USERNAME ",
            "order": "ASC",
        },
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 200
    # COMPAT: search/role/status 不做 strip()；repository/service 自行处理。
    assert filters.search == " foo "
    assert filters.role == "admin"
    assert filters.status == "inactive"
    assert filters.sort_field == " username "
    assert filters.sort_order == "asc"


@pytest.mark.unit
def test_user_list_filters_query_fallbacks_invalid_sort_order_to_default() -> None:
    query = validate_or_raise(UserListFiltersQuery, {"order": "weird"})
    assert query.to_filters().sort_order == "desc"


@pytest.mark.unit
def test_user_list_filters_query_coerces_blank_role_and_status_to_none() -> None:
    query = validate_or_raise(UserListFiltersQuery, {"role": "", "status": ""})
    filters = query.to_filters()
    assert filters.role is None
    assert filters.status is None
