from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.repositories.database_statistics_repository import DatabaseStatisticsRepository
from app.settings import Settings


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    settings = Settings.load()
    app = create_app(init_scheduler_on_start=False, settings=settings)
    app.config["TESTING"] = True
    return app


def _ensure_database_statistics_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["instance_databases"],
            ],
        )


@pytest.mark.unit
def test_database_statistics_repository_distinguishes_inactive_and_deleted_databases(app) -> None:
    _ensure_database_statistics_tables(app)

    with app.app_context():
        instance = Instance(name="prod-mysql-1", db_type="mysql", host="127.0.0.1", port=3306, is_active=True)
        db.session.add(instance)
        db.session.flush()

        db.session.add_all(
            [
                InstanceDatabase(instance_id=instance.id, database_name="app_db", is_active=True),
                InstanceDatabase(instance_id=instance.id, database_name="archive_db", is_active=False),
                InstanceDatabase(
                    instance_id=instance.id,
                    database_name="deleted_db",
                    is_active=False,
                    deleted_at=datetime(2026, 3, 16, 12, 0, tzinfo=UTC),
                ),
            ],
        )
        db.session.commit()

        summary = DatabaseStatisticsRepository.fetch_summary()

        assert summary["total_databases"] == 3
        assert summary["active_databases"] == 1
        assert summary["inactive_databases"] == 1
        assert summary["deleted_databases"] == 1
