import pytest

from app.settings import Settings


@pytest.mark.unit
def test_settings_cache_options_ttl_can_be_overridden(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_OPTIONS_TTL", "60")
    settings = Settings.load()
    assert settings.cache_options_ttl_seconds == 60


@pytest.mark.unit
def test_settings_cache_options_ttl_rejects_negative(monkeypatch) -> None:
    monkeypatch.setenv("CACHE_OPTIONS_TTL", "-1")
    with pytest.raises(ValueError, match=r"CACHE_OPTIONS_TTL"):
        Settings.load()
