from __future__ import annotations

import pytest

from app import db
from app.models.instance import Instance
from app.models.instance_config_snapshot import InstanceConfigSnapshot
from app.services.config_sync import instance_audit_sync_actions_service as actions_module


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


def _get_csrf_token(client) -> str:
    response = client.get("/api/v1/auth/csrf-token")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    csrf_token = payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    return csrf_token


@pytest.mark.unit
def test_api_v1_instances_audit_info_requires_auth(client) -> None:
    response = client.get("/api/v1/instances/1/audit-info")
    assert response.status_code == 401


@pytest.mark.unit
def test_api_v1_instances_audit_info_non_sqlserver_returns_supported_false(app, auth_client) -> None:
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
        instance_id = instance.id

    response = auth_client.get(f"/api/v1/instances/{instance_id}/audit-info")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("supported") is False
    assert data.get("config_key") == "audit_info"
    assert data.get("db_type") == "mysql"


@pytest.mark.unit
def test_api_v1_instances_audit_info_sqlserver_returns_snapshot(app, auth_client) -> None:
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

        db.session.add(
            InstanceConfigSnapshot(
                instance_id=instance.id,
                db_type="sqlserver",
                config_key="audit_info",
                snapshot={
                    "version": 1,
                    "supported": True,
                    "db_type": "sqlserver",
                    "server_audits": [{"name": "audit-main", "enabled": True}],
                    "audit_specifications": [],
                    "database_audit_specifications": [],
                    "errors": [],
                    "meta": {},
                },
                facts={
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
            ),
        )
        db.session.commit()
        instance_id = instance.id

    response = auth_client.get(f"/api/v1/instances/{instance_id}/audit-info")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("supported") is True
    assert data.get("config_key") == "audit_info"
    assert data.get("snapshot", {}).get("server_audits", [])[0].get("name") == "audit-main"
    assert data.get("facts", {}).get("has_audit") is True


@pytest.mark.unit
def test_api_v1_instances_sync_audit_info_rejects_unsupported_db_type(app, auth_client) -> None:
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
        instance_id = instance.id

    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/actions/sync-audit-info",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 409

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True


@pytest.mark.unit
def test_api_v1_instances_sync_audit_info_contract(app, auth_client, monkeypatch) -> None:
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
        instance_id = instance.id

    def _fake_sync(self, *, instance_id, actor_id=None):  # type: ignore[no-untyped-def]
        del self
        del instance_id
        del actor_id
        return actions_module.InstanceAuditSyncActionResult(
            success=True,
            message="审计信息同步成功",
            result={"session_id": "session-1", "summary": {"audit_count": 1}},
        )

    monkeypatch.setattr(actions_module.InstanceAuditSyncActionsService, "sync_instance_audit_info", _fake_sync)

    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        f"/api/v1/instances/{instance_id}/actions/sync-audit-info",
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("session_id") == "session-1"
    assert data.get("summary", {}).get("audit_count") == 1
