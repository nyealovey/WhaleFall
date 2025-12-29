import pytest

from app import db
from app.constants import DatabaseType
from app.models.instance import Instance


def _ensure_accounts_sync_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )


@pytest.mark.unit
def test_api_v1_accounts_sync_requires_auth(client) -> None:
    csrf_response = client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    response = client.post("/api/v1/accounts/actions/sync-all", headers=headers)
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.post("/api/v1/accounts/actions/sync", json={"instance_id": 1}, headers=headers)
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_accounts_sync_endpoints_contract(app, auth_client, monkeypatch) -> None:
    _ensure_accounts_sync_tables(app)

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
        instance_id = instance.id

    class _DummyThread:
        name = "dummy_sync_accounts_manual_batch"

    class _DummyAccountSyncService:
        @staticmethod
        def sync_accounts(instance, sync_type):  # noqa: ANN001
            return {
                "success": True,
                "message": "实例账户同步成功",
                "synced_count": 1,
                "added_count": 0,
                "modified_count": 0,
                "removed_count": 0,
            }

    import app.api.v1.namespaces.accounts as api_module

    monkeypatch.setattr(api_module, "_launch_background_sync", lambda created_by, session_id: _DummyThread())
    monkeypatch.setattr(api_module, "accounts_sync_service", _DummyAccountSyncService())

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    sync_all_response = auth_client.post("/api/v1/accounts/actions/sync-all", headers=headers)
    assert sync_all_response.status_code == 200
    sync_all_payload = sync_all_response.get_json()
    assert isinstance(sync_all_payload, dict)
    assert sync_all_payload.get("success") is True
    sync_all_data = sync_all_payload.get("data")
    assert isinstance(sync_all_data, dict)
    assert isinstance(sync_all_data.get("session_id"), str)

    sync_response = auth_client.post(
        "/api/v1/accounts/actions/sync",
        json={"instance_id": instance_id},
        headers=headers,
    )
    assert sync_response.status_code == 200
    sync_payload = sync_response.get_json()
    assert isinstance(sync_payload, dict)
    assert sync_payload.get("success") is True
    sync_data = sync_payload.get("data")
    assert isinstance(sync_data, dict)
    result = sync_data.get("result")
    assert isinstance(result, dict)
    assert {"status", "message", "success"}.issubset(result.keys())


@pytest.mark.unit
def test_api_v1_accounts_sync_failure_contract(app, auth_client, monkeypatch) -> None:
    _ensure_accounts_sync_tables(app)

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
        instance_id = instance.id

    class _DummyAccountSyncService:
        @staticmethod
        def sync_accounts(instance, sync_type):  # noqa: ANN001
            return {"success": False, "message": "实例账户同步失败"}

    import app.api.v1.namespaces.accounts as api_module

    monkeypatch.setattr(api_module, "accounts_sync_service", _DummyAccountSyncService())

    csrf_response = auth_client.get("/api/v1/auth/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    response = auth_client.post(
        "/api/v1/accounts/actions/sync",
        json={"instance_id": instance_id},
        headers=headers,
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
    assert payload.get("message_code") == "INVALID_REQUEST"
