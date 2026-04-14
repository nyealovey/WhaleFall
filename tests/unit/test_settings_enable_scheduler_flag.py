import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_enable_scheduler_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")

    settings = Settings.load()

    assert settings.enable_scheduler is False


@pytest.mark.unit
def test_settings_loads_veeam_backup_objects_limit(monkeypatch) -> None:
    monkeypatch.setenv("VEEAM_BACKUP_OBJECTS_LIMIT", "1500")

    settings = Settings.load()

    assert settings.veeam_backup_objects_limit == 1500
    assert settings.to_flask_config()["VEEAM_BACKUP_OBJECTS_LIMIT"] == 1500


@pytest.mark.unit
def test_settings_loads_veeam_token_timeout_and_retry_controls(monkeypatch) -> None:
    monkeypatch.setenv("VEEAM_TOKEN_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("VEEAM_TOKEN_RETRY_ATTEMPTS", "4")
    monkeypatch.setenv("VEEAM_TOKEN_RETRY_BACKOFF_SECONDS", "0")

    settings = Settings.load()
    flask_config = settings.to_flask_config()

    assert settings.veeam_token_timeout_seconds == 7
    assert settings.veeam_token_retry_attempts == 4
    assert settings.veeam_token_retry_backoff_seconds == 0
    assert flask_config["VEEAM_TOKEN_TIMEOUT_SECONDS"] == 7
    assert flask_config["VEEAM_TOKEN_RETRY_ATTEMPTS"] == 4
    assert flask_config["VEEAM_TOKEN_RETRY_BACKOFF_SECONDS"] == 0
