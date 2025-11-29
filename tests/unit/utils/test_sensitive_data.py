import pytest

from app.utils.sensitive_data import scrub_sensitive_fields


@pytest.mark.unit
def test_scrub_sensitive_fields_masks_nested_values() -> None:
    payload = {
        "username": "demo",
        "password": "Pa55word",
        "profile": {"token": "abc", "display": "Demo"},
        "secrets": [{"secret": "value"}, {"note": "safe"}],
    }

    sanitized = scrub_sensitive_fields(payload)

    assert sanitized["password"] == "***"
    assert sanitized["profile"]["token"] == "***"
    assert sanitized["secrets"][0]["secret"] == "***"
    assert sanitized["profile"]["display"] == "Demo"


@pytest.mark.unit
def test_scrub_sensitive_fields_supports_extra_keys() -> None:
    payload = {"custom": "value", "api_key": "key"}

    sanitized = scrub_sensitive_fields(payload, extra_keys=["custom"])

    assert sanitized["custom"] == "***"
    assert sanitized["api_key"] == "***"
