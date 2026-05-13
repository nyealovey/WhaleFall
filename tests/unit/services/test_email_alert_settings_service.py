from __future__ import annotations

from dataclasses import dataclass

import pytest

from app import create_app
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.settings import Settings
from app.utils.password_crypto_utils import get_password_manager


@dataclass(slots=True)
class _DummySettings:
    recipients_json: list[str]
    global_enabled: bool = False
    database_capacity_enabled: bool = False
    database_capacity_percent_threshold: int = 30
    database_capacity_absolute_gb_threshold: int = 20
    account_sync_failure_enabled: bool = False
    database_sync_failure_enabled: bool = False
    privileged_account_enabled: bool = False
    backup_issue_enabled: bool = False
    feishu_enabled: bool = False
    feishu_webhook_url_encrypted: str | None = None

    def set_feishu_webhook_url(self, webhook_url: str) -> None:
        self.feishu_webhook_url_encrypted = get_password_manager().encrypt_password(webhook_url)

    def get_feishu_webhook_url(self) -> str:
        if not self.feishu_webhook_url_encrypted:
            return ""
        return get_password_manager().decrypt_password(self.feishu_webhook_url_encrypted)

    def get_feishu_webhook_url_masked(self) -> str | None:
        webhook_url = self.get_feishu_webhook_url()
        if not webhook_url:
            return None
        prefix, separator, token = webhook_url.rpartition("/")
        return f"{prefix}{separator}**********{token[-4:]}"

    def to_dict(self) -> dict[str, object]:
        masked_url = self.get_feishu_webhook_url_masked()
        return {
            "global_enabled": self.global_enabled,
            "recipients": self.recipients_json,
            "database_capacity_enabled": self.database_capacity_enabled,
            "database_capacity_percent_threshold": self.database_capacity_percent_threshold,
            "database_capacity_absolute_gb_threshold": self.database_capacity_absolute_gb_threshold,
            "account_sync_failure_enabled": self.account_sync_failure_enabled,
            "database_sync_failure_enabled": self.database_sync_failure_enabled,
            "privileged_account_enabled": self.privileged_account_enabled,
            "backup_issue_enabled": self.backup_issue_enabled,
            "feishu_enabled": self.feishu_enabled,
            "feishu_webhook_url_configured": masked_url is not None,
            "feishu_webhook_url_masked": masked_url,
        }


class _StubRepository:
    def __init__(self) -> None:
        self.settings = _DummySettings(recipients_json=["ops@example.com"])
        self.added: list[_DummySettings] = []

    def get_settings(self):
        return self.settings

    def add_settings(self, settings) -> None:
        self.settings = settings
        self.added.append(settings)


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


class _StubFeishuSender:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def send_text(self, *, title: str, text_body: str, webhook_url: str | None = None) -> None:
        self.calls.append(
            {
                "title": title,
                "text_body": text_body,
                "webhook_url": webhook_url,
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


@pytest.mark.unit
def test_email_alert_settings_service_encrypts_masks_and_clears_feishu_webhook_url() -> None:
    repository = _StubRepository()
    service = EmailAlertSettingsService(repository=repository, sender=_StubSender())
    app = create_app(init_scheduler_on_start=False, settings=Settings.load())
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"

    with app.app_context():
        updated = service.update_settings(
            {
                "global_enabled": True,
                "recipients": ["ops@example.com"],
                "database_capacity_enabled": False,
                "database_capacity_percent_threshold": 30,
                "database_capacity_absolute_gb_threshold": 20,
                "account_sync_failure_enabled": False,
                "database_sync_failure_enabled": False,
                "privileged_account_enabled": False,
                "backup_issue_enabled": False,
                "feishu_enabled": True,
                "feishu_webhook_url": webhook_url,
                "clear_feishu_webhook_url": False,
            },
        )

        assert updated.feishu_enabled is True
        assert updated.feishu_webhook_url_encrypted
        assert updated.feishu_webhook_url_encrypted != webhook_url
        view_payload = service.build_view_payload()
        settings_payload = view_payload["settings"]
        assert isinstance(settings_payload, dict)
        assert settings_payload["feishu_webhook_url_configured"] is True
        assert settings_payload["feishu_webhook_url_masked"] == (
            "https://open.feishu.cn/open-apis/bot/v2/hook/**********oken"
        )
        assert "feishu_webhook_url" not in settings_payload
        assert service.get_feishu_webhook_url() == webhook_url

        service.update_settings(
            {
                "global_enabled": True,
                "recipients": ["ops@example.com"],
                "database_capacity_enabled": False,
                "database_capacity_percent_threshold": 30,
                "database_capacity_absolute_gb_threshold": 20,
                "account_sync_failure_enabled": False,
                "database_sync_failure_enabled": False,
                "privileged_account_enabled": False,
                "backup_issue_enabled": False,
                "feishu_enabled": True,
                "feishu_webhook_url": "",
                "clear_feishu_webhook_url": False,
            },
        )
        assert service.get_feishu_webhook_url() == webhook_url

        service.update_settings(
            {
                "global_enabled": True,
                "recipients": ["ops@example.com"],
                "database_capacity_enabled": False,
                "database_capacity_percent_threshold": 30,
                "database_capacity_absolute_gb_threshold": 20,
                "account_sync_failure_enabled": False,
                "database_sync_failure_enabled": False,
                "privileged_account_enabled": False,
                "backup_issue_enabled": False,
                "feishu_enabled": False,
                "feishu_webhook_url": "",
                "clear_feishu_webhook_url": True,
            },
        )
        assert service.get_feishu_webhook_url() == ""


@pytest.mark.unit
def test_email_alert_settings_service_send_test_feishu_uses_given_webhook_url() -> None:
    feishu_sender = _StubFeishuSender()
    service = EmailAlertSettingsService(
        repository=_StubRepository(),
        sender=_StubSender(),
        feishu_sender=feishu_sender,
    )
    app = create_app(init_scheduler_on_start=False, settings=Settings.load())
    webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/typed-token"

    with app.app_context():
        result = service.send_test_feishu(webhook_url=webhook_url)

    assert result["sent"] is True
    assert result["webhook_url_configured"] is True
    assert feishu_sender.calls
    assert feishu_sender.calls[0]["webhook_url"] == webhook_url
    assert "飞书测试" in str(feishu_sender.calls[0]["title"])


@pytest.mark.unit
def test_email_alert_settings_service_send_test_feishu_uses_saved_webhook_url_when_input_empty() -> None:
    repository = _StubRepository()
    saved_webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/saved-token"
    feishu_sender = _StubFeishuSender()
    service = EmailAlertSettingsService(
        repository=repository,
        sender=_StubSender(),
        feishu_sender=feishu_sender,
    )
    app = create_app(init_scheduler_on_start=False, settings=Settings.load())

    with app.app_context():
        repository.settings.set_feishu_webhook_url(saved_webhook_url)
        result = service.send_test_feishu(webhook_url="")

    assert result["sent"] is True
    assert result["webhook_url_configured"] is True
    assert feishu_sender.calls[0]["webhook_url"] is None


@pytest.mark.unit
def test_email_alert_settings_service_send_test_feishu_requires_webhook_url() -> None:
    service = EmailAlertSettingsService(
        repository=_StubRepository(),
        sender=_StubSender(),
        feishu_sender=_StubFeishuSender(),
    )
    app = create_app(init_scheduler_on_start=False, settings=Settings.load())

    with app.app_context(), pytest.raises(Exception, match="飞书机器人 URL"):
        service.send_test_feishu(webhook_url="")
