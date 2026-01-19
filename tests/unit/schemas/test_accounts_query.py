import pytest

from app.schemas.accounts_query import AccountsFiltersQuery, AccountsLedgersListQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_accounts_filters_query_defaults() -> None:
    query = validate_or_raise(AccountsFiltersQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 20
    assert filters.search == ""
    assert filters.instance_id is None
    assert filters.include_deleted is False
    assert filters.is_locked is None
    assert filters.is_superuser is None
    assert filters.plugin == ""
    assert filters.tags == []
    assert filters.classification == ""
    assert filters.classification_filter == ""
    assert filters.db_type is None


@pytest.mark.unit
def test_accounts_filters_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        AccountsFiltersQuery,
        {
            "page": 0,
            "limit": 999,
            "search": "  foo  ",
            "instance_id": 123,
            "include_deleted": True,
            "is_locked": " TRUE ",
            "is_superuser": "false",
            "plugin": "  mysql_native_password  ",
            "tags": [" a ", "", " b "],
            "classification": "  all  ",
            "db_type": " MYSQL ",
        },
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 200
    assert filters.search == "foo"
    assert filters.instance_id == 123
    assert filters.include_deleted is True
    assert filters.is_locked == "true"
    assert filters.is_superuser == "false"
    assert filters.plugin == "mysql_native_password"
    assert filters.tags == ["a", "b"]
    assert filters.classification == "all"
    assert filters.classification_filter == ""
    assert filters.db_type == "mysql"


@pytest.mark.unit
def test_accounts_ledgers_list_query_defaults() -> None:
    query = validate_or_raise(AccountsLedgersListQuery, {})
    assert query.sort_field == "username"
    assert query.sort_order == "asc"
