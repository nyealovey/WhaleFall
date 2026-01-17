import pytest

from app.schemas.credentials_query import CredentialListFiltersQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_credential_list_filters_query_defaults() -> None:
    query = validate_or_raise(CredentialListFiltersQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 20
    assert filters.search == ""
    assert filters.credential_type is None
    assert filters.db_type is None
    assert filters.status is None
    assert filters.tags == []
    assert filters.sort_field == "created_at"
    assert filters.sort_order == "desc"


@pytest.mark.unit
def test_credential_list_filters_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        CredentialListFiltersQuery,
        {
            "page": 0,
            "limit": 999,
            "search": "  foo  ",
            "credential_type": " password ",
            "db_type": " mysql ",
            "status": " ACTIVE ",
            "tags": [" a ", "", " b "],
            "sort": " CREATED_AT ",
            "order": "ASC",
        },
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 200
    assert filters.search == "foo"
    assert filters.credential_type == "password"
    assert filters.db_type == "mysql"
    assert filters.status == "active"
    assert filters.tags == ["a", "b"]
    assert filters.sort_field == "created_at"
    assert filters.sort_order == "asc"


@pytest.mark.unit
def test_credential_list_filters_query_status_rejects_unknown_value() -> None:
    query = validate_or_raise(CredentialListFiltersQuery, {"status": "weird"})
    assert query.to_filters().status is None


@pytest.mark.unit
def test_credential_list_filters_query_choice_all_and_blank_to_none() -> None:
    query = validate_or_raise(CredentialListFiltersQuery, {"db_type": "all", "credential_type": "  "})
    filters = query.to_filters()
    assert filters.db_type is None
    assert filters.credential_type is None


@pytest.mark.unit
def test_credential_list_filters_query_fallbacks_invalid_sort_order_to_default() -> None:
    query = validate_or_raise(CredentialListFiltersQuery, {"order": "weird"})
    assert query.to_filters().sort_order == "desc"
