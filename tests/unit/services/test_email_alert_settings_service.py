from __future__ import annotations

from dataclasses import dataclass

import pytest

from app import create_app
from app.settings import Settings
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService


@dataclass(slots=True)
class _DummySettings:
    recipients_json: list[str]


class _StubRepository:
    def get_settings(self):
        return _DummySettings(recipients_json=["ops@example.com"])


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


@pytest.mark.unit
def test_email_alert_settings_service_send_test_email_uses_given_recipients() -> None:
    sender = _StubSender()
    service = EmailAlertSettingsService(repository=_StubRepository(), sender=sender)
    app = create_app(init_scheduler_on_start=False, settings=Settings.load())

    with app.app_context():
        result = service.send_test_email(recipients=["dba@example.com"])

    assert result["sent"] is True
    assert result["recipient_count"] == 1
    assert result["recipients"] == ["dba@example.com"]
    assert sender.calls
    assert sender.calls[0]["recipients"] == ["dba@example.com"]
    assert "测试邮件" in str(sender.calls[0]["subject"])
