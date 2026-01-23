import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_enable_scheduler_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_SCHEDULER", "false")

    settings = Settings.load()

    assert settings.enable_scheduler is False
