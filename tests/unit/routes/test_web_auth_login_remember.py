"""Web 登录 remember 选项行为测试.

目标:
- 未勾选“记住我”时不应下发 remember_token
- 勾选“记住我”时 remember_token 过期时间为 7 天
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http.cookies import SimpleCookie

import pytest

from app import db
from app.core.constants import HttpHeaders
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
def test_web_auth_login_without_remember_does_not_set_remember_cookie(app, client) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[db.metadata.tables["users"]],
        )
        user = User(username="admin", password="TestPass1", role="admin")
        db.session.add(user)
        db.session.commit()

        csrf_token = _get_csrf_token(client)
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "TestPass1"},
            headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        set_cookie_headers = response.headers.getlist("Set-Cookie")
        assert not any(value.startswith("remember_token=") for value in set_cookie_headers)


@pytest.mark.unit
def test_web_auth_login_with_remember_sets_remember_cookie_expire_in_7_days(app, client, monkeypatch) -> None:
    import flask_login.login_manager as login_manager_module

    fixed_now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

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
        response = client.post(
            "/auth/login",
            data={"username": "admin", "password": "TestPass1", "remember": "on"},
            headers={HttpHeaders.X_CSRF_TOKEN: csrf_token},
            follow_redirects=False,
        )
        assert response.status_code == 302

        set_cookie_headers = response.headers.getlist("Set-Cookie")
        remember_cookie_header = next(
            (value for value in set_cookie_headers if value.startswith("remember_token=")),
            None,
        )
        assert isinstance(remember_cookie_header, str)

        cookie = SimpleCookie()
        cookie.load(remember_cookie_header)
        expires_raw = cookie["remember_token"]["expires"]
        assert isinstance(expires_raw, str)

        expires_at = parsedate_to_datetime(expires_raw).astimezone(timezone.utc)
        assert expires_at == fixed_now + timedelta(days=7)

