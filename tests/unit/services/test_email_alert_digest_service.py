from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.services.alerts.email_alert_digest_service import EmailAlertDigestService


@dataclass(slots=True)
class _DummySettings:
    global_enabled: bool = True
    recipients_json: list[str] = None  # type: ignore[assignment]


@dataclass(slots=True)
class _DummyEvent:
    id: int
    alert_type: str
    payload_json: dict[str, object]
    occurred_at: datetime


class _StubRepository:
    def __init__(self, events: list[_DummyEvent]) -> None:
        self.events = events
        self.marked: list[tuple[list[int], datetime]] = []

    def list_pending_digest_events(self) -> list[_DummyEvent]:
        return list(self.events)

    def mark_events_digest_sent(self, event_ids: list[int], sent_at: datetime) -> None:
        self.marked.append((list(event_ids), sent_at))


class _StubSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def is_ready(self) -> bool:
        return True

    def send_email(self, *, recipients: list[str], subject: str, text_body: str) -> None:
        self.calls.append(
            {
                "recipients": list(recipients),
                "subject": subject,
                "text_body": text_body,
            },
        )


class _StubSettingsService:
    def __init__(self, settings: _DummySettings) -> None:
        self.settings = settings

    def get_or_create_settings(self) -> _DummySettings:
        return self.settings


@pytest.mark.unit
def test_email_alert_digest_service_sends_pending_events_and_marks_sent() -> None:
    settings = _DummySettings(global_enabled=True, recipients_json=["ops@example.com"])
    events = [
        _DummyEvent(
            id=1,
            alert_type="database_capacity_growth",
            payload_json={"database_name": "orders", "size_change_percent": 42.0},
            occurred_at=datetime(2026, 3, 17, 1, 0, tzinfo=UTC),
        ),
        _DummyEvent(
            id=2,
            alert_type="database_sync_failure",
            payload_json={"instance_name": "prod-mysql-1", "error_message": "连接失败"},
            occurred_at=datetime(2026, 3, 17, 2, 0, tzinfo=UTC),
        ),
    ]
    repository = _StubRepository(events)
    sender = _StubSender()
    service = EmailAlertDigestService(
        repository=repository,
        sender=sender,
        settings_service=_StubSettingsService(settings),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 9, 0, tzinfo=UTC))

    assert summary["sent"] is True
    assert summary["event_count"] == 2
    assert sender.calls
    assert sender.calls[0]["recipients"] == ["ops@example.com"]
    assert "邮件告警汇总" in str(sender.calls[0]["subject"])
    assert "orders" in str(sender.calls[0]["text_body"])
    assert repository.marked == [([1, 2], datetime(2026, 3, 17, 9, 0, tzinfo=UTC))]
