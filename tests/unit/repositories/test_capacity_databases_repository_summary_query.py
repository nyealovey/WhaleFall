from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.types.capacity_databases import DatabaseAggregationsSummaryFilters
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.repositories.capacity_databases_repository import CapacityDatabasesRepository


@pytest.mark.unit
def test_build_summary_query_avoids_tuple_in_and_uses_period_start_partition_key() -> None:
    """汇总查询应避免构造超大的 tuple IN 参数列表，并显式使用 period_start(分区键)过滤."""
    engine = create_engine("sqlite:///:memory:")
    session = sessionmaker(bind=engine)()

    repository = CapacityDatabasesRepository(session=session)
    filters = DatabaseAggregationsSummaryFilters(
        instance_id=None,
        db_type=None,
        database_name=None,
        database_id=None,
        period_type="daily",
        start_date=date(2026, 1, 20),
        end_date=date(2026, 1, 26),
    )

    query = repository._build_latest_aggregations_summary_query(filters)
    sql = str(query.statement.compile(compile_kwargs={"literal_binds": True}))

    assert "max(database_size_aggregations.period_start)" in sql
    assert "latest_period_start" in sql
    assert " IN ((" not in sql
    assert "database_size_aggregations.period_start >= '2026-01-20'" in sql
    assert "database_size_aggregations.period_start <= '2026-01-26'" in sql


@pytest.mark.unit
def test_summarize_latest_aggregations_returns_latest_values_within_range() -> None:
    engine = create_engine("sqlite:///:memory:")
    for model in (Instance, InstanceDatabase, DatabaseSizeAggregation):
        model.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    session.add(
        Instance(
            id=1,
            name="i1",
            db_type="postgresql",
            host="h",
            port=5432,
            is_active=True,
        ),
    )
    session.add_all(
        [
            InstanceDatabase(id=1, instance_id=1, database_name="db1", is_active=True),
            InstanceDatabase(id=2, instance_id=1, database_name="db2", is_active=True),
        ],
    )

    now = datetime.now(timezone.utc)
    session.add_all(
        [
            DatabaseSizeAggregation(
                id=1,
                instance_id=1,
                database_name="db1",
                period_type="daily",
                period_start=date(2026, 1, 25),
                period_end=date(2026, 1, 25),
                avg_size_mb=100,
                max_size_mb=120,
                min_size_mb=90,
                data_count=1,
                size_change_mb=0,
                size_change_percent=0,
                growth_rate=0,
                calculated_at=now,
                created_at=now,
            ),
            DatabaseSizeAggregation(
                id=2,
                instance_id=1,
                database_name="db1",
                period_type="daily",
                period_start=date(2026, 1, 26),
                period_end=date(2026, 1, 26),
                avg_size_mb=110,
                max_size_mb=130,
                min_size_mb=95,
                data_count=1,
                size_change_mb=0,
                size_change_percent=0,
                growth_rate=0,
                calculated_at=now,
                created_at=now,
            ),
            DatabaseSizeAggregation(
                id=3,
                instance_id=1,
                database_name="db2",
                period_type="daily",
                period_start=date(2026, 1, 25),
                period_end=date(2026, 1, 25),
                avg_size_mb=50,
                max_size_mb=60,
                min_size_mb=45,
                data_count=1,
                size_change_mb=0,
                size_change_percent=0,
                growth_rate=0,
                calculated_at=now,
                created_at=now,
            ),
        ],
    )
    session.commit()

    repository = CapacityDatabasesRepository(session=session)
    result = repository.summarize_latest_aggregations(
        DatabaseAggregationsSummaryFilters(
            instance_id=None,
            db_type=None,
            database_name=None,
            database_id=None,
            period_type="daily",
            start_date=date(2026, 1, 20),
            end_date=date(2026, 1, 26),
        ),
    )

    assert result == (2, 1, 160, 80.0, 130)

