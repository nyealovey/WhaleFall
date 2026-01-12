from datetime import date

import pytest

from app import db
from app.core.constants import DatabaseType
from app.models.database_size_aggregation import DatabaseSizeAggregation
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase


def _ensure_capacity_databases_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_databases"],
                db.metadata.tables["database_size_aggregations"],
            ],
        )


@pytest.mark.unit
def test_api_v1_capacity_databases_requires_auth(client) -> None:
    response = client.get(
        "/api/v1/capacity/databases?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get(
        "/api/v1/capacity/databases/summary?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_capacity_databases_endpoints_contract(app, auth_client) -> None:
    _ensure_capacity_databases_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type=DatabaseType.MYSQL,
            host="127.0.0.1",
            port=3306,
            description=None,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        database = InstanceDatabase(
            instance_id=instance.id,
            database_name="db1",
            is_active=True,
        )
        db.session.add(database)
        db.session.commit()

        aggregation_date = date(2025, 12, 24)
        db.session.add(
            DatabaseSizeAggregation(
                id=1,
                instance_id=instance.id,
                database_name=database.database_name,
                period_type="daily",
                period_start=aggregation_date,
                period_end=aggregation_date,
                avg_size_mb=512,
                max_size_mb=512,
                min_size_mb=512,
                data_count=1,
                size_change_mb=0,
                size_change_percent=0.0,
                growth_rate=0.0,
            ),
        )
        db.session.commit()

    response = auth_client.get(
        "/api/v1/capacity/databases?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())
    items = data.get("items")
    assert isinstance(items, list)
    assert len(items) == 1

    item = items[0]
    assert isinstance(item, dict)
    assert {
        "id",
        "instance_id",
        "database_name",
        "period_type",
        "period_start",
        "period_end",
        "avg_size_mb",
        "size_change_mb",
        "size_change_percent",
        "instance",
    }.issubset(item.keys())

    summary_response = auth_client.get(
        "/api/v1/capacity/databases/summary?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
    )
    assert summary_response.status_code == 200
    summary_payload = summary_response.get_json()
    assert isinstance(summary_payload, dict)
    assert summary_payload.get("success") is True
    summary_data = summary_payload.get("data")
    assert isinstance(summary_data, dict)
    summary = summary_data.get("summary")
    assert isinstance(summary, dict)
    assert {
        "total_databases",
        "total_instances",
        "total_size_mb",
        "avg_size_mb",
        "max_size_mb",
        "growth_rate",
    }.issubset(summary.keys())
