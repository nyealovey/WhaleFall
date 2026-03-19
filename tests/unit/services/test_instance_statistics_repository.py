from __future__ import annotations

import pytest

from app import create_app, db
from app.repositories.instance_statistics_repository import InstanceStatisticsRepository
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


def _ensure_instance_statistics_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )


@pytest.mark.unit
def test_instance_statistics_repository_counts_total_current_active_inactive_and_deleted_instances(app) -> None:
    from app.models.instance import Instance

    _ensure_instance_statistics_tables(app)

    with app.app_context():
        db.session.add_all(
            [
                Instance(name="mysql-active", db_type="mysql", host="127.0.0.1", port=3306, is_active=True),
                Instance(name="mysql-disabled", db_type="mysql", host="127.0.0.2", port=3307, is_active=False),
                Instance(
                    name="mysql-deleted",
                    db_type="mysql",
                    host="127.0.0.3",
                    port=3308,
                    is_active=True,
                    deleted_at=time_utils.now(),
                ),
            ],
        )
        db.session.commit()

        summary = InstanceStatisticsRepository.fetch_summary()

        assert summary["total_instances"] == 3
        assert summary["current_instances"] == 2
        assert summary["active_instances"] == 1
        assert summary["disabled_instances"] == 1
        assert summary["deleted_instances"] == 1
        assert summary["normal_instances"] == 1
