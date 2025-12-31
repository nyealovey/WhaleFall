import pytest


@pytest.mark.unit
def test_api_v1_health_cache_requires_auth(client) -> None:
    response = client.get("/api/v1/health/cache")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_health_cache_contract(auth_client, monkeypatch) -> None:
    import app.api.v1.namespaces.health as api_module

    class _DummyCacheService:
        @staticmethod
        def health_check() -> bool:
            return True

    monkeypatch.setattr(api_module, "_get_cache_service", lambda: _DummyCacheService())

    response = auth_client.get("/api/v1/health/cache")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"healthy", "status"}.issubset(data.keys())


@pytest.mark.unit
def test_api_v1_health_detailed_contract(client, monkeypatch) -> None:
    import app.api.v1.namespaces.health as api_module

    monkeypatch.setattr(api_module, "check_database_health", lambda: {"healthy": True}, raising=False)
    monkeypatch.setattr(api_module, "check_cache_health", lambda: {"healthy": True}, raising=False)
    monkeypatch.setattr(api_module, "check_system_health", lambda: {"healthy": True}, raising=False)

    response = client.get("/api/v1/health/detailed")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"status", "timestamp", "version", "components"}.issubset(data.keys())
    components = data.get("components")
    assert isinstance(components, dict)
    assert {"database", "cache", "system"}.issubset(components.keys())
