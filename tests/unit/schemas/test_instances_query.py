import pytest

from app.schemas.instances_query import InstanceListFiltersQuery, InstancesExportQuery, InstancesOptionsQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_instance_list_filters_query_defaults() -> None:
    query = validate_or_raise(InstanceListFiltersQuery, {})
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 20
    assert filters.sort_field == "id"
    assert filters.sort_order == "desc"
    assert filters.search == ""
    assert filters.db_type == ""
    assert filters.status == ""
    assert filters.tags == []
    assert filters.include_deleted is False


@pytest.mark.unit
def test_instance_list_filters_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        InstanceListFiltersQuery,
        {
            "page": 0,
            "limit": 999,
            "sort": " NAME ",
            "order": "ASC",
            "search": "  foo  ",
            "db_type": " mysql ",
            "status": "  disabled ",
            "tags": [" a ", "", " b "],
            "include_deleted": True,
        },
    )
    filters = query.to_filters()

    assert filters.page == 1
    assert filters.limit == 100
    assert filters.sort_field == "name"
    assert filters.sort_order == "asc"
    assert filters.search == "foo"
    assert filters.db_type == "mysql"
    assert filters.status == "disabled"
    assert filters.tags == ["a", "b"]
    assert filters.include_deleted is True


@pytest.mark.unit
def test_instance_list_filters_query_fallbacks_invalid_sort_order_to_default() -> None:
    query = validate_or_raise(InstanceListFiltersQuery, {"order": "weird"})
    filters = query.to_filters()

    assert filters.sort_order == "desc"


@pytest.mark.unit
def test_instances_options_query_strips_blank_to_none() -> None:
    query = validate_or_raise(InstancesOptionsQuery, {"db_type": "  mysql  "})
    assert query.db_type == "mysql"

    blank = validate_or_raise(InstancesOptionsQuery, {"db_type": "   "})
    assert blank.db_type is None


@pytest.mark.unit
def test_instances_export_query_strips_params() -> None:
    query = validate_or_raise(InstancesExportQuery, {"search": " foo ", "db_type": " mysql "})
    assert query.search == "foo"
    assert query.db_type == "mysql"
