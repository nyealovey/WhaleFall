import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_fails_fast_when_password_encryption_key_invalid(monkeypatch) -> None:
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-secret-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("PASSWORD_ENCRYPTION_KEY", "Whalefall_prod1232")

    with pytest.raises(ValueError, match=r"PASSWORD_ENCRYPTION_KEY.*Fernet\.generate_key"):
        Settings.load()
