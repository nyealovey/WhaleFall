import pytest

from app import db
from app.constants import HttpHeaders
from app.models.user import User


def _get_csrf_token(client) -> str:
    response = client.get("/api/v1/auth/csrf-token")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    csrf_token = payload.get("data", {}).get("csrf_token")
    assert isinstance(csrf_token, str)
    return csrf_token


@pytest.mark.unit
def test_api_v1_auth_csrf_token_contract(client) -> None:
    response = client.get("/api/v1/auth/csrf-token")
    assert response.status_code == 200

    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("success") is True
    assert payload.get("error") is False

    data = payload.get("data")
    assert isinstance(data, dict)
    assert isinstance(data.get("csrf_token"), str)


@pytest.mark.unit
def test_api_v1_auth_login_me_refresh_logout_contract(app, client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        csrf_token = _get_csrf_token(client)

        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "TestPass1"},
            headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
        )
        assert login_response.status_code == 200
        login_payload = login_response.get_json()
        assert isinstance(login_payload, dict)
        assert login_payload.get("success") is True
        assert login_payload.get("error") is False

        login_data = login_payload.get("data")
        assert isinstance(login_data, dict)
        access_token = login_data.get("access_token")
        refresh_token = login_data.get("refresh_token")
        assert isinstance(access_token, str)
        assert isinstance(refresh_token, str)

        user_data = login_data.get("user")
        assert isinstance(user_data, dict)
        assert user_data.get("id") == user.id
        assert user_data.get("username") == "admin"

        me_response = client.get(
            "/api/v1/auth/me",
            headers={HttpHeaders.AUTHORIZATION: f"Bearer {access_token}"},
        )
        assert me_response.status_code == 200
        me_payload = me_response.get_json()
        assert isinstance(me_payload, dict)
        assert me_payload.get("success") is True

        me_data = me_payload.get("data")
        assert isinstance(me_data, dict)
        assert me_data.get("id") == user.id
        assert me_data.get("username") == "admin"

        csrf_token = _get_csrf_token(client)
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={},
            headers={
                HttpHeaders.AUTHORIZATION: f"Bearer {refresh_token}",
                HttpHeaders.X_CSRF_TOKEN: csrf_token,
            },
        )
        assert refresh_response.status_code == 200
        refresh_payload = refresh_response.get_json()
        assert isinstance(refresh_payload, dict)
        assert refresh_payload.get("success") is True
        refresh_data = refresh_payload.get("data")
        assert isinstance(refresh_data, dict)
        assert isinstance(refresh_data.get("access_token"), str)
        assert refresh_data.get("token_type") == "Bearer"
        assert isinstance(refresh_data.get("expires_in"), int)

        csrf_token = _get_csrf_token(client)
        logout_response = client.post(
            "/api/v1/auth/logout",
            json={},
            headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
        )
        assert logout_response.status_code == 200
        logout_payload = logout_response.get_json()
        assert isinstance(logout_payload, dict)
        assert logout_payload.get("success") is True
        assert logout_payload.get("error") is False


@pytest.mark.unit
def test_api_v1_auth_change_password_invalid_old_password_contract(app, client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        csrf_token = _get_csrf_token(client)
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "TestPass1"},
            headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
        )
        assert login_response.status_code == 200

        csrf_token = _get_csrf_token(client)
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "WrongPass1",
                "new_password": "NewPass1",
                "confirm_password": "NewPass1",
            },
            headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
        )

        assert response.status_code == 401
        payload = response.get_json()
        assert isinstance(payload, dict)
        assert payload.get("error") is True
        assert payload.get("message_code") == "INVALID_OLD_PASSWORD"
