from __future__ import annotations

import pytest

from app import create_app, db
from app.models.instance import Instance
from app.services.instances.batch_service import InstanceBatchDeletionService
from app.services.instances.instance_write_service import InstanceWriteService
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


def _ensure_instances_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )


@pytest.mark.unit
def test_instance_write_service_soft_delete_disables_and_restore_reenables(app) -> None:
    _ensure_instances_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = InstanceWriteService()
        service.soft_delete(instance.id)
        db.session.flush()
        db.session.refresh(instance)

        assert instance.deleted_at is not None
        assert instance.is_active is False

        service.restore(instance.id)
        db.session.flush()
        db.session.refresh(instance)

        assert instance.deleted_at is None
        assert instance.is_active is True


@pytest.mark.unit
def test_instance_batch_soft_delete_disables_instance(app) -> None:
    _ensure_instances_tables(app)

    with app.app_context():
        instance = Instance(
            name="instance-batch",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = InstanceBatchDeletionService()
        result = service.delete_instances([instance.id], deletion_mode="soft")
        db.session.flush()
        db.session.refresh(instance)

        assert result["deleted_count"] == 1
        assert result["deletion_mode"] == "soft"
        assert instance.deleted_at is not None
        assert instance.is_active is False
