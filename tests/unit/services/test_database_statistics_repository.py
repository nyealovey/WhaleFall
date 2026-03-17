from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app import create_app, db
from app.models.instance import Instance
from app.models.instance_database import InstanceDatabase
from app.repositories.database_statistics_repository import DatabaseStatisticsRepository
from app.settings import Settings
from app.utils.time_utils import time_utils


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


@pytest.mark.unit
def test_database_statistics_repository_includes_disabled_instances_and_excludes_deleted_instances(app) -> None:
    _ensure_database_statistics_tables(app)

    with app.app_context():
        disabled_instance = Instance(
            name="disabled-mysql-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=False,
        )
        deleted_instance = Instance(
            name="deleted-mysql-1",
            db_type="mysql",
            host="127.0.0.2",
            port=3307,
            is_active=True,
            deleted_at=time_utils.now(),
        )
        db.session.add_all([disabled_instance, deleted_instance])
        db.session.flush()

        db.session.add_all(
            [
                InstanceDatabase(instance_id=disabled_instance.id, database_name="visible_db", is_active=True),
                InstanceDatabase(instance_id=deleted_instance.id, database_name="hidden_db", is_active=True),
            ],
        )
        db.session.commit()

        summary = DatabaseStatisticsRepository.fetch_summary()

        assert summary["total_databases"] == 1
        assert summary["active_databases"] == 1
        assert summary["total_instances"] == 1
