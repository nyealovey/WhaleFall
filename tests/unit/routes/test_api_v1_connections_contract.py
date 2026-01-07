import pytest

from app import db
from app.constants import HttpHeaders
from app.constants.system_constants import ErrorMessages
from app.models.credential import Credential
from app.models.instance import Instance
from app.services.connection_adapters.connection_test_service import ConnectionTestService
from app.utils.time_utils import time_utils


def _get_csrf_token(client) -> str:
    response = client.get("/api/v1/auth/csrf-token")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    csrf_token = payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    return csrf_token


@pytest.mark.unit
def test_api_v1_connections_requires_auth(client) -> None:
    response = client.get("/api/v1/instances/1/connection-status")
    assert response.status_code == 401

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("success") is False
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_connections_validate_params_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["credentials"],
            ],
        )

        credential = Credential(
            name="cred-1",
            credential_type="database",
            username="root",
            password="Passw0rdA",
        )
        db.session.add(credential)
        db.session.commit()
        credential_id = int(credential.id)

    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        "/api/v1/instances/actions/validate-connection-params",
        json={
            "db_type": "mysql",
            "port": 3306,
            "credential_id": credential_id,
        },
        headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False


@pytest.mark.unit
def test_api_v1_connections_batch_test_contract(auth_client) -> None:
    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        "/api/v1/instances/actions/batch-test-connections",
        json={"instance_ids": [999]},
        headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"results", "summary"}.issubset(data.keys())

    results = data.get("results")
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0].get("instance_id") == 999
    assert results[0].get("success") is False

    summary = data.get("summary")
    assert isinstance(summary, dict)
    assert summary.get("total") == 1
    assert summary.get("success") == 0
    assert summary.get("failed") == 1


@pytest.mark.unit
def test_api_v1_connections_status_contract(app, auth_client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
            ],
        )

        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
            last_connected=time_utils.now(),
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = int(instance.id)

    response = auth_client.get(f"/api/v1/instances/{instance_id}/connection-status")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert {
        "instance_id",
        "instance_name",
        "db_type",
        "host",
        "port",
        "last_connected",
        "status",
        "is_active",
    }.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_connections_test_connection_missing_payload_contract(auth_client) -> None:
    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        "/api/v1/instances/actions/test-connection",
        json={},
        headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
    )
    assert response.status_code == 400

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
    assert payload.get("message_code") == "VALIDATION_ERROR"


@pytest.mark.unit
def test_api_v1_connections_test_connection_failure_contract(app, auth_client, monkeypatch) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["credentials"],
            ],
        )

        credential = Credential(
            name="cred-1",
            credential_type="database",
            username="root",
            password="Passw0rdA",
        )
        db.session.add(credential)
        db.session.commit()
        credential_id = int(credential.id)

    def _fake_test_connection(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {
            "success": False,
            "message": ErrorMessages.DATABASE_CONNECTION_ERROR,
            "error_code": "CONNECTION_FAILED",
            "error_id": "test-error-id",
        }

    monkeypatch.setattr(ConnectionTestService, "test_connection", _fake_test_connection)

    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        "/api/v1/instances/actions/test-connection",
        json={
            "db_type": "postgresql",
            "host": "127.0.0.1",
            "port": 5432,
            "credential_id": credential_id,
        },
        headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
    )
    assert response.status_code == 409

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is False
    assert payload.get("error") is True
    assert payload.get("message_code") == "DATABASE_CONNECTION_ERROR"


@pytest.mark.unit
def test_api_v1_connections_test_connection_success_contract(app, auth_client, monkeypatch) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["credentials"],
            ],
        )

        credential = Credential(
            name="cred-1",
            credential_type="database",
            username="root",
            password="Passw0rdA",
        )
        db.session.add(credential)
        db.session.commit()
        credential_id = int(credential.id)

    def _fake_test_connection(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        return {"success": True, "message": "OK"}

    monkeypatch.setattr(ConnectionTestService, "test_connection", _fake_test_connection)

    csrf_token = _get_csrf_token(auth_client)
    response = auth_client.post(
        "/api/v1/instances/actions/test-connection",
        json={
            "db_type": "postgresql",
            "host": "127.0.0.1",
            "port": 5432,
            "credential_id": credential_id,
        },
        headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
    )
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert data.get("success") is True
    assert "result" not in data
