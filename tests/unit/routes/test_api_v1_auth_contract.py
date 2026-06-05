import pytest

from app import db
from app.core.constants import HttpHeaders
from app.models.user import User
from datetime import UTC


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
def test_api_v1_auth_session_login_me_logout_contract(app, client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        anonymous_session_response = client.get("/api/v1/auth/session")
        assert anonymous_session_response.status_code == 200
        anonymous_session_payload = anonymous_session_response.get_json()
        assert isinstance(anonymous_session_payload, dict)
        anonymous_session_data = anonymous_session_payload.get("data")
        assert isinstance(anonymous_session_data, dict)
        assert anonymous_session_data.get("authenticated") is False
        assert anonymous_session_data.get("user") is None
        assert anonymous_session_data.get("permissions") == []
        assert anonymous_session_data.get("auth_model") == "session"
        assert isinstance(anonymous_session_data.get("csrf_token"), str)

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
        assert "access_token" not in login_data
        assert "refresh_token" not in login_data
        assert login_data.get("auth_model") == "session"
        assert isinstance(login_data.get("csrf_token"), str)

        user_data = login_data.get("user")
        assert isinstance(user_data, dict)
        assert user_data.get("id") == user.id
        assert user_data.get("username") == "admin"

        session_response = client.get("/api/v1/auth/session")
        assert session_response.status_code == 200
        session_payload = session_response.get_json()
        assert isinstance(session_payload, dict)
        session_data = session_payload.get("data")
        assert isinstance(session_data, dict)
        assert session_data.get("authenticated") is True
        assert session_data.get("auth_model") == "session"
        assert isinstance(session_data.get("csrf_token"), str)
        assert "admin" in session_data.get("permissions", [])
        session_user = session_data.get("user")
        assert isinstance(session_user, dict)
        assert session_user.get("id") == user.id

        me_response = client.get("/api/v1/auth/me")
        assert me_response.status_code == 200
        me_payload = me_response.get_json()
        assert isinstance(me_payload, dict)
        assert me_payload.get("success") is True

        me_data = me_payload.get("data")
        assert isinstance(me_data, dict)
        assert me_data.get("id") == user.id
        assert me_data.get("username") == "admin"

        refresh_response = client.post("/api/v1/auth/refresh", json={})
        assert refresh_response.status_code == 404

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

        logged_out_session_response = client.get("/api/v1/auth/session")
        assert logged_out_session_response.status_code == 200
        logged_out_payload = logged_out_session_response.get_json()
        assert isinstance(logged_out_payload, dict)
        logged_out_data = logged_out_payload.get("data")
        assert isinstance(logged_out_data, dict)
        assert logged_out_data.get("authenticated") is False


@pytest.mark.unit
def test_api_v1_auth_me_requires_session(client) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert payload.get("error") is True
    assert payload.get("message_code") == "AUTHENTICATION_REQUIRED"


@pytest.mark.unit
def test_api_v1_auth_login_sets_remember_cookie_expire_in_7_days(app, client, monkeypatch) -> None:
    from datetime import datetime, timedelta
    from email.utils import parsedate_to_datetime
    from http.cookies import SimpleCookie

    import flask_login.login_manager as login_manager_module

    fixed_now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)

    class _FixedDatetime(datetime):
        @classmethod
        def utcnow(cls):
            return fixed_now.replace(tzinfo=None)

    monkeypatch.setattr(login_manager_module, "datetime", _FixedDatetime)

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

        set_cookie_headers = login_response.headers.getlist("Set-Cookie")
        remember_cookie_header = next(
            (value for value in set_cookie_headers if value.startswith("remember_token=")),
            None,
        )
        assert isinstance(remember_cookie_header, str)

        cookie = SimpleCookie()
        cookie.load(remember_cookie_header)
        expires_raw = cookie["remember_token"]["expires"]
        assert isinstance(expires_raw, str)

        expires_at = parsedate_to_datetime(expires_raw).astimezone(UTC)
        assert expires_at == fixed_now + timedelta(days=7)


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
