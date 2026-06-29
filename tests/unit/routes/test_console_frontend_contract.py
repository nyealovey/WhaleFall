import pytest

from app import create_app
from app.settings import Settings


@pytest.mark.unit
def test_console_frontend_routes_are_removed(client) -> None:
    for path in ("/console", "/console/instances", "/console/assets/app.js", "/console/static/css/fonts.css"):
        response = client.get(path)
        assert response.status_code == 404


@pytest.mark.unit
def test_console_frontend_does_not_replace_existing_login_page(client) -> None:
    response = client.get("/auth/login")

    assert response.status_code == 200
    assert b"/console/assets/" not in response.data
    assert b"app/static" not in response.data


@pytest.mark.unit
def test_legacy_templates_respect_forwarded_old_prefix(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.setenv("PROXY_FIX_X_PREFIX", "1")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    app = create_app(init_scheduler_on_start=False, settings=Settings.load())
    client = app.test_client()
    response = client.get("/about", headers={"X-Forwarded-Prefix": "/old"})

    assert response.status_code == 200
    assert b'href="/old/auth/login"' in response.data
    assert b'href="/about"' in response.data
    assert b'href="/dashboard"' in response.data
    assert b'href="/old/"' in response.data
    assert b"/old/static/" in response.data
    assert b'href="/old/about"' not in response.data
    assert b'href="/auth/login"' not in response.data
    assert b'href="/static/' not in response.data
    assert b'src="/static/' not in response.data
