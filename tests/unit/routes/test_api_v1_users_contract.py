import pytest


def _get_csrf_token(client) -> str:
    csrf_response = client.get("/auth/api/csrf-token")
    assert csrf_response.status_code == 200
    csrf_payload = csrf_response.get_json()
    assert isinstance(csrf_payload, dict)
    csrf_token = csrf_payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    return csrf_token


@pytest.mark.unit
def test_api_v1_users_requires_auth(client) -> None:
    csrf_token = _get_csrf_token(client)
    headers = {"X-CSRFToken": csrf_token}

    response = client.get("/api/v1/users")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.get("/api/v1/users/stats")
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.post(
        "/api/v1/users",
        json={"username": "u1", "role": "user", "password": "TestPass1"},
        headers=headers,
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.put(
        "/api/v1/users/1",
        json={"username": "u2", "role": "user", "is_active": True},
        headers=headers,
    )
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"

    response = client.delete("/api/v1/users/1", headers=headers)
    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_users_endpoints_contract(auth_client) -> None:
    csrf_token = _get_csrf_token(auth_client)
    headers = {"X-CSRFToken": csrf_token}

    list_response = auth_client.get("/api/v1/users")
    assert list_response.status_code == 200
    payload = list_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"items", "total", "page", "pages", "limit"}.issubset(data.keys())

    create_response = auth_client.post(
        "/api/v1/users",
        json={"username": "user_01", "role": "user", "password": "TestPass1", "is_active": True},
        headers=headers,
    )
    assert create_response.status_code == 201
    payload = create_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    user = data.get("user")
    assert isinstance(user, dict)
    user_id = user.get("id")
    assert isinstance(user_id, int)

    detail_response = auth_client.get(f"/api/v1/users/{user_id}")
    assert detail_response.status_code == 200
    payload = detail_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    update_response = auth_client.put(
        f"/api/v1/users/{user_id}",
        json={"username": "user_01_renamed", "role": "user", "is_active": False},
        headers=headers,
    )
    assert update_response.status_code == 200
    payload = update_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True

    stats_response = auth_client.get("/api/v1/users/stats")
    assert stats_response.status_code == 200
    payload = stats_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    data = payload.get("data")
    assert isinstance(data, dict)
    assert {"total", "active", "inactive", "admin", "user"}.issubset(data.keys())

    delete_response = auth_client.delete(f"/api/v1/users/{user_id}", headers=headers)
    assert delete_response.status_code == 200
    payload = delete_response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
