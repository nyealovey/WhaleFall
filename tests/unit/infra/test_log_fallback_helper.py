import pytest

from app.infra import route_safety


@pytest.mark.unit
def test_log_fallback_always_sets_fallback_fields(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Logger:
        def warning(self, event, **kwargs):  # type: ignore[no-untyped-def]
            captured["event"] = event
            captured["kwargs"] = kwargs

        def error(self, event, **kwargs):  # type: ignore[no-untyped-def]
            captured["event"] = event
            captured["kwargs"] = kwargs

    monkeypatch.setattr(route_safety, "get_logger", lambda _name: _Logger())

    route_safety.log_fallback(
        "warning",
        "fallback_event",
        module="test",
        action="action",
        fallback_reason="reason",
    )

    payload = captured.get("kwargs")
    assert isinstance(payload, dict)
    assert payload.get("fallback") is True
    assert payload.get("fallback_reason") == "reason"
