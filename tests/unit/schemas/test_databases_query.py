from datetime import date

import pytest

from app.core.constants.validation_limits import DATABASE_TABLE_SIZES_LIMIT_MAX
from app.core.exceptions import ValidationError
from app.schemas.databases_query import (
    DatabaseLedgersQuery,
    DatabasesOptionsQuery,
    DatabasesSizesQuery,
    DatabaseTableSizesQuery,
)
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_databases_options_query_rejects_offset() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(DatabasesOptionsQuery, {"instance_id": 1, "offset": "10"})

    assert "不支持 offset" in str(excinfo.value)


@pytest.mark.unit
def test_databases_options_query_clamps_limit_and_computes_offset() -> None:
    query = validate_or_raise(DatabasesOptionsQuery, {"instance_id": 5, "page": 2, "limit": 1000})

    assert query.page == 2
    assert query.limit == 1000

    filters = query.to_filters()
    assert filters.instance_id == 5
    assert filters.limit == 1000
    assert filters.offset == 1000


@pytest.mark.unit
def test_databases_options_query_rejects_limit_out_of_range() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(DatabasesOptionsQuery, {"instance_id": 5, "limit": 1001})


@pytest.mark.unit
def test_database_ledgers_query_normalizes_values_and_splits_tags() -> None:
    query = validate_or_raise(
        DatabaseLedgersQuery,
        {
            "search": "  foo  ",
            "db_type": "   ",
            "tags": ["a", "b,c", "  ", ",d"],
            "page": 1,
            "limit": 200,
        },
    )

    assert query.search == "foo"
    assert query.db_type == "all"
    assert query.tags == ["a", "b", "c", "d"]
    assert query.page == 1
    assert query.limit == 200


@pytest.mark.unit
def test_databases_sizes_query_requires_instance_id() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(DatabasesSizesQuery, {"instance_id": None})

    assert "缺少 instance_id" in str(excinfo.value)


@pytest.mark.unit
def test_databases_sizes_query_rejects_offset() -> None:
    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(DatabasesSizesQuery, {"instance_id": 1, "offset": "10"})

    assert "不支持 offset" in str(excinfo.value)


@pytest.mark.unit
def test_databases_sizes_query_parses_dates_and_pagination() -> None:
    query = validate_or_raise(
        DatabasesSizesQuery,
        {
            "instance_id": 1,
            "limit": 100,
            "page": 2,
            "start_date": "2026-01-01",
        },
    )

    assert query.limit == 100
    assert query.page == 2
    assert query.start_date == date(2026, 1, 1)

    options = query.to_options()
    assert options.limit == 100
    assert options.offset == 100


@pytest.mark.unit
def test_databases_sizes_query_rejects_non_positive_limit() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(DatabasesSizesQuery, {"instance_id": 1, "limit": 0})


@pytest.mark.unit
def test_databases_sizes_query_rejects_invalid_dates() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(DatabasesSizesQuery, {"instance_id": 1, "start_date": "not-a-date"})


@pytest.mark.unit
def test_database_table_sizes_query_validates_limit_max_and_rejects_offset() -> None:
    with pytest.raises(ValidationError):
        validate_or_raise(DatabaseTableSizesQuery, {"limit": DATABASE_TABLE_SIZES_LIMIT_MAX + 1})

    with pytest.raises(ValidationError) as excinfo:
        validate_or_raise(DatabaseTableSizesQuery, {"offset": "10"})
    assert "不支持 offset" in str(excinfo.value)

    with pytest.raises(ValidationError):
        validate_or_raise(DatabaseTableSizesQuery, {"limit": 0})
