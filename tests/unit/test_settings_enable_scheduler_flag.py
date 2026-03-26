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
