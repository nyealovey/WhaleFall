from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import create_app, db
from app.models.instance import Instance
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.models.sync_instance_record import SyncInstanceRecord
from app.models.sync_session import SyncSession
from app.services.config_sync.instance_audit_sync_actions_service import InstanceAuditSyncActionsService
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


def _ensure_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["sync_sessions"],
                db.metadata.tables["sync_instance_records"],
                db.metadata.tables["instance_config_snapshots"],
            ],
        )


@pytest.mark.unit
def test_instance_audit_sync_actions_service_persists_snapshot_and_session(app) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="sqlserver-1",
            db_type="sqlserver",
            host="127.0.0.1",
            port=1433,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        class _FakeAuditSyncService:
            def sync_instance_audit(self, *, instance):  # type: ignore[no-untyped-def]
                del instance
                return {
                    "snapshot": {
                        "version": 1,
                        "supported": True,
                        "db_type": "sqlserver",
                        "server_audits": [{"name": "audit-main", "enabled": True, "target_type": "FILE"}],
                        "audit_specifications": [],
                        "database_audit_specifications": [],
                        "errors": [],
                        "meta": {},
                    },
                    "facts": {
                        "version": 1,
                        "supported": True,
                        "has_audit": True,
                        "audit_count": 1,
                        "enabled_audit_count": 1,
                        "specification_count": 0,
                        "covered_database_count": 0,
                        "target_types": ["FILE"],
                        "failure_policies": [],
                        "warnings": [],
                    },
                    "summary": {
                        "audit_count": 1,
                        "enabled_audit_count": 1,
                        "specification_count": 0,
                        "covered_database_count": 0,
                    },
                }

        service = InstanceAuditSyncActionsService(sync_service=_FakeAuditSyncService())
        result = service.sync_instance_audit_info(instance_id=instance.id)

        assert result.success is True
        assert result.http_status == 200
        assert isinstance(result.result.get("session_id"), str)

        snapshot = InstanceConfigSnapshot.query.filter_by(instance_id=instance.id, config_key="audit_info").one()
        assert snapshot.db_type == "sqlserver"
        assert snapshot.snapshot["server_audits"][0]["name"] == "audit-main"
        assert snapshot.facts["has_audit"] is True

        session = SyncSession.query.filter_by(session_id=result.result["session_id"]).one()
        assert session.sync_category == "config"
        assert session.status == "completed"

        record = SyncInstanceRecord.query.filter_by(session_id=session.session_id, instance_id=instance.id).one()
        assert record.sync_category == "config"
        assert record.status == "completed"


@pytest.mark.unit
def test_instance_audit_sync_actions_service_rejects_unsupported_db_type(app) -> None:
    _ensure_tables(app)

    with app.app_context():
        instance = Instance(
            name="mysql-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()

        service = InstanceAuditSyncActionsService(sync_service=SimpleNamespace())
        result = service.sync_instance_audit_info(instance_id=instance.id)

        assert result.success is False
        assert result.http_status == 409
        assert result.message_key == "INVALID_REQUEST"
