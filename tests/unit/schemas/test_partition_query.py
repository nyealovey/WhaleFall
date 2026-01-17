import pytest

from app.schemas.partition_query import PartitionCoreMetricsQuery, PartitionsListQuery
from app.schemas.validation import validate_or_raise


@pytest.mark.unit
def test_partitions_list_query_defaults() -> None:
    query = validate_or_raise(PartitionsListQuery, {})
    assert query.search == ""
    assert query.table_type == ""
    assert query.status == ""
    assert query.sort_field == "name"
    assert query.sort_order == "asc"
    assert query.page == 1
    assert query.limit == 20


@pytest.mark.unit
def test_partitions_list_query_normalizes_and_clamps() -> None:
    query = validate_or_raise(
        PartitionsListQuery,
        {
            "search": "  foo  ",
            "table_type": "  base  ",
            "status": "  active  ",
            "sort": "  NAME  ",
            "order": "  desc  ",
            "page": 0,
            "limit": 999,
        },
    )
    assert query.search == "foo"
    assert query.table_type == "base"
    assert query.status == "active"
    assert query.sort_field == "NAME"
    assert query.sort_order == "desc"
    assert query.page == 1
    assert query.limit == 200


@pytest.mark.unit
def test_partition_core_metrics_query_defaults() -> None:
    query = validate_or_raise(PartitionCoreMetricsQuery, {})
    assert query.period_type == "daily"
    assert query.days == 7


@pytest.mark.unit
def test_partition_core_metrics_query_normalizes_and_compat_days_zero() -> None:
    query = validate_or_raise(PartitionCoreMetricsQuery, {"period_type": " WEEKLY ", "days": 0})
    assert query.period_type == "weekly"
    assert query.days == 7
