import pytest

import app.services.cache_service as cache_service_module

from app import db
from app.models.instance import Instance
from app.services.account_classification.orchestrator import AccountClassificationService


@pytest.mark.unit
def test_api_v1_cache_requires_auth(client) -> None:
    response = client.get("/api/v1/cache/stats")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    csrf_response = client.get("/auth/api/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    clear_all_response = client.post("/api/v1/cache/clear/all", json={}, headers=headers)
    assert clear_all_response.status_code == 401
    payload = clear_all_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_cache_endpoints_contract(app, auth_client, monkeypatch) -> None:
    class _DummyCacheService:
        @staticmethod
        def get_cache_stats() -> dict[str, object]:
            return {"keys": 1}

        @staticmethod
        def invalidate_user_cache(instance_id: int, username: str) -> bool:
            del instance_id, username
            return True

        @staticmethod
        def invalidate_instance_cache(instance_id: int) -> bool:
            del instance_id
            return True

        @staticmethod
        def get_classification_rules_by_db_type_cache(db_type: str):  # noqa: ANN001
            del db_type
            return [{"id": 1}]

    monkeypatch.setattr(cache_service_module, "cache_service", _DummyCacheService())
    monkeypatch.setattr(AccountClassificationService, "invalidate_cache", lambda self: True)
    monkeypatch.setattr(AccountClassificationService, "invalidate_db_type_cache", lambda self, db_type: True)

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["instances"],
                db.metadata.tables["unified_logs"],
            ],
        )
        instance = Instance(
            name="instance-1",
            db_type="mysql",
            host="127.0.0.1",
            port=3306,
            is_active=True,
        )
        db.session.add(instance)
        db.session.commit()
        instance_id = instance.id

    csrf_response = auth_client.get("/auth/api/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    headers = {"X-CSRFToken": csrf_token}

    stats_response = auth_client.get("/api/v1/cache/stats")
    assert stats_response.status_code == 200
    payload = stats_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "stats" in data

    classification_stats_response = auth_client.get("/api/v1/cache/classification/stats")
    assert classification_stats_response.status_code == 200
    payload = classification_stats_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"cache_stats", "db_type_stats", "cache_enabled"}.issubset(data.keys())

    clear_user_response = auth_client.post(
        "/api/v1/cache/clear/user",
        json={"instance_id": instance_id, "username": "u1"},
        headers=headers,
    )
    assert clear_user_response.status_code == 200
    payload = clear_user_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    clear_instance_response = auth_client.post(
        "/api/v1/cache/clear/instance",
        json={"instance_id": instance_id},
        headers=headers,
    )
    assert clear_instance_response.status_code == 200
    payload = clear_instance_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    clear_all_response = auth_client.post(
        "/api/v1/cache/clear/all",
        json={},
        headers=headers,
    )
    assert clear_all_response.status_code == 200
    payload = clear_all_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert "cleared_count" in data

    classification_clear_response = auth_client.post(
        "/api/v1/cache/classification/clear",
        json={},
        headers=headers,
    )
    assert classification_clear_response.status_code == 200
    payload = classification_clear_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    classification_clear_db_type_response = auth_client.post(
        "/api/v1/cache/classification/clear/mysql",
        json={},
        headers=headers,
    )
    assert classification_clear_db_type_response.status_code == 200
    payload = classification_clear_db_type_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

