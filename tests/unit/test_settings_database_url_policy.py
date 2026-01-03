import os

import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_fails_fast_when_database_url_missing_in_production(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key")
    # Prevent `load_dotenv()` from injecting a value from local `.env`.
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(ValueError, match=r"DATABASE_URL.*production"):
        Settings.load()


@pytest.mark.unit
def test_settings_does_not_mutate_dyld_library_path(monkeypatch) -> None:
    original = "/opt/oracle/instantclient"
    monkeypatch.setenv("DYLD_LIBRARY_PATH", original)

    Settings.load()

    assert os.environ.get("DYLD_LIBRARY_PATH") == original

