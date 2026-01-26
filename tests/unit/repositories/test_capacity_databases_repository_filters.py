from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.types.capacity_databases import DatabaseAggregationsFilters
from app.repositories.capacity_databases_repository import CapacityDatabasesRepository


@pytest.mark.unit
def test_apply_filters_uses_period_start_bounds_for_partition_pruning() -> None:
    """确保日期范围过滤包含 period_start 约束(分区键),避免扫描全量分区."""
    engine = create_engine("sqlite:///:memory:")
    session = sessionmaker(bind=engine)()

    repository = CapacityDatabasesRepository(session=session)
    filters = DatabaseAggregationsFilters(
        instance_id=None,
        db_type=None,
        database_name=None,
        database_id=None,
        period_type="daily",
        start_date=date(2026, 1, 20),
        end_date=date(2026, 1, 26),
        page=1,
        limit=20,
        get_all=True,
    )

    query = repository._apply_filters(repository._base_query(), filters, resolved_database_name=None)
    sql = str(query.statement.compile(compile_kwargs={"literal_binds": True}))

    assert "database_size_aggregations.period_start >= '2026-01-20'" in sql
    assert "database_size_aggregations.period_start <= '2026-01-26'" in sql
    assert "database_size_aggregations.period_end <= '2026-01-26'" in sql
    assert "database_size_aggregations.period_end >= '2026-01-20'" not in sql
