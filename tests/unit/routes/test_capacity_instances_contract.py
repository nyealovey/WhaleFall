from datetime import date

import pytest
from sqlalchemy import text

from app import create_app, db
from app.constants import DatabaseType
from app.models.instance import Instance
from app.models.instance_size_aggregation import InstanceSizeAggregation
from app.models.instance_size_stat import InstanceSizeStat
from app.models.user import User


@pytest.mark.unit
def test_capacity_instances_contract() -> None:
    app = create_app(init_scheduler_on_start=False)
    app.config["TESTING"] = True

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["users"],
                db.metadata.tables["instances"],
                db.metadata.tables["unified_logs"],
            ],
        )
        db.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS instance_size_aggregations (
                    id INTEGER NOT NULL,
                    instance_id INTEGER NOT NULL,
                    period_type VARCHAR(20) NOT NULL,
                    period_start DATE NOT NULL,
                    period_end DATE NOT NULL,
                    total_size_mb INTEGER NOT NULL,
                    avg_size_mb INTEGER NOT NULL,
                    max_size_mb INTEGER NOT NULL,
                    min_size_mb INTEGER NOT NULL,
                    data_count INTEGER NOT NULL,
                    database_count INTEGER NOT NULL,
                    avg_database_count NUMERIC(10,2),
                    max_database_count INTEGER,
                    min_database_count INTEGER,
                    total_size_change_mb INTEGER,
                    total_size_change_percent NUMERIC(10,2),
                    database_count_change INTEGER,
                    database_count_change_percent NUMERIC(10,2),
                    growth_rate NUMERIC(10,2),
                    trend_direction VARCHAR(20),
                    calculated_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL,
                    PRIMARY KEY (id, period_start),
                    FOREIGN KEY(instance_id) REFERENCES instances(id)
                );
                """,
            ),
        )
        db.session.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS instance_size_stats (
                    id INTEGER NOT NULL,
                    instance_id INTEGER NOT NULL,
                    total_size_mb INTEGER NOT NULL,
                    database_count INTEGER NOT NULL,
                    collected_date DATE NOT NULL,
                    collected_at DATETIME NOT NULL,
                    is_deleted BOOLEAN NOT NULL,
                    deleted_at DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME,
                    PRIMARY KEY (id, collected_date),
                    FOREIGN KEY(instance_id) REFERENCES instances(id)
                );
                """,
            ),
        )
        db.session.commit()

        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)

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

        aggregation_date = date(2025, 12, 24)
        db.session.add(
            InstanceSizeAggregation(
                id=1,
                instance_id=instance.id,
                period_type="daily",
                period_start=aggregation_date,
                period_end=aggregation_date,
                total_size_mb=1024,
                avg_size_mb=1024,
                max_size_mb=1024,
                min_size_mb=1024,
                data_count=1,
                database_count=3,
                avg_database_count=3.0,
                max_database_count=3,
                min_database_count=3,
                total_size_change_mb=0,
                total_size_change_percent=0.0,
                database_count_change=0,
                database_count_change_percent=0.0,
                growth_rate=0.0,
                trend_direction="stable",
            ),
        )
        db.session.add(
            InstanceSizeStat(
                id=1,
                instance_id=instance.id,
                total_size_mb=1024,
                database_count=3,
                collected_date=aggregation_date,
            ),
        )
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as session:
            session["_user_id"] = str(user.id)

        response = client.get(
            "/capacity/api/instances?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
        )
        assert response.status_code == 200

        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("success") is True
        assert payload.get("error") is False
        assert {"message", "timestamp"}.issubset(payload.keys())

        data = payload.get("data")
        assert isinstance(data, dict)
        assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())

        items = data.get("items")
        assert isinstance(items, list)
        assert len(items) == 1

        item = items[0]
        assert isinstance(item, dict)
        expected_item_keys = {
            "id",
            "instance_id",
            "period_type",
            "period_start",
            "period_end",
            "total_size_mb",
            "avg_size_mb",
            "database_count",
            "total_size_change_mb",
            "total_size_change_percent",
            "instance",
        }
        assert expected_item_keys.issubset(item.keys())
        assert isinstance(item.get("instance"), dict)

        summary_response = client.get(
            "/capacity/api/instances/summary?period_type=daily&start_date=2025-12-24&end_date=2025-12-24",
        )
        assert summary_response.status_code == 200

        summary_payload = summary_response.get_json()
        assert isinstance(summary_payload, dict)
        assert summary_payload.get("success") is True
        assert summary_payload.get("error") is False
        assert {"message", "timestamp"}.issubset(summary_payload.keys())

        summary_data = summary_payload.get("data")
        assert isinstance(summary_data, dict)
        summary = summary_data.get("summary")
        assert isinstance(summary, dict)
        assert {"total_instances", "total_size_mb", "avg_size_mb", "max_size_mb", "period_type", "source"}.issubset(
            summary.keys(),
        )
