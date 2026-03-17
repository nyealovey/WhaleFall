import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_loads_mail_alert_env(monkeypatch) -> None:
    monkeypatch.setenv("MAIL_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("MAIL_SMTP_PORT", "2525")
    monkeypatch.setenv("MAIL_USE_TLS", "true")
    monkeypatch.setenv("MAIL_USE_SSL", "false")
    monkeypatch.setenv("MAIL_TIMEOUT_SECONDS", "15")
    monkeypatch.setenv("MAIL_FROM_ADDRESS", "whalefall@example.com")
    monkeypatch.setenv("MAIL_FROM_NAME", "WhaleFall Alerts")

    settings = Settings.load()

    assert settings.mail_smtp_host == "smtp.example.com"
    assert settings.mail_smtp_port == 2525
    assert settings.mail_use_tls is True
    assert settings.mail_use_ssl is False
    assert settings.mail_timeout_seconds == 15
    assert settings.mail_from_address == "whalefall@example.com"
    assert settings.mail_from_name == "WhaleFall Alerts"
