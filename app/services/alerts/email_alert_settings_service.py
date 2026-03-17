"""邮件告警配置服务."""

from __future__ import annotations

from typing import Any, cast

from flask import current_app

from app import db
from app.core.exceptions import ValidationError
from app.models.email_alert_setting import EmailAlertSetting
from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.services.alerts.email_sender import EmailSender
from app.utils.time_utils import time_utils


class EmailAlertSettingsService:
    """邮件告警配置服务."""

    def __init__(
        self,
        repository: EmailAlertsRepository | None = None,
        sender: EmailSender | None = None,
    ) -> None:
        self._repository = repository or EmailAlertsRepository()
        self._sender = sender or EmailSender()

    @staticmethod
    def _build_default_settings() -> EmailAlertSetting:
        settings = EmailAlertSetting()
        settings.global_enabled = False
        settings.recipients_json = []
        settings.database_capacity_enabled = False
        settings.database_capacity_percent_threshold = 30
        settings.database_capacity_absolute_gb_threshold = 20
        settings.account_sync_failure_enabled = False
        settings.database_sync_failure_enabled = False
        settings.privileged_account_enabled = False
        return settings

    def get_or_create_settings(self) -> EmailAlertSetting:
        settings = self._repository.get_settings()
        if settings is not None:
            return settings
        return self._build_default_settings()

    def update_settings(self, payload: dict[str, object]) -> EmailAlertSetting:
        payload_dict = cast("dict[str, Any]", payload)
        settings = self._repository.get_settings()
        if settings is None:
            settings = self._build_default_settings()
            self._repository.add_settings(settings)

        settings.global_enabled = bool(payload_dict["global_enabled"])
        settings.recipients_json = list(cast("list[str]", payload_dict["recipients"]))
        settings.database_capacity_enabled = bool(payload_dict["database_capacity_enabled"])
        settings.database_capacity_percent_threshold = int(payload_dict["database_capacity_percent_threshold"])
        settings.database_capacity_absolute_gb_threshold = int(payload_dict["database_capacity_absolute_gb_threshold"])
        settings.account_sync_failure_enabled = bool(payload_dict["account_sync_failure_enabled"])
        settings.database_sync_failure_enabled = bool(payload_dict["database_sync_failure_enabled"])
        settings.privileged_account_enabled = bool(payload_dict["privileged_account_enabled"])
        db.session.commit()
        return settings

    def build_view_payload(self) -> dict[str, object]:
        settings = self.get_or_create_settings()
        return {
            "smtp_ready": self._is_smtp_ready(),
            "from_address": current_app.config.get("MAIL_FROM_ADDRESS"),
            "from_name": current_app.config.get("MAIL_FROM_NAME"),
            "settings": settings.to_dict(),
        }

    def send_test_email(self, *, recipients: list[str]) -> dict[str, object]:
        normalized_recipients = [item.strip() for item in recipients if item.strip()]
        if not normalized_recipients:
            raise ValidationError("测试邮件至少需要一个收件人")
        if not self._sender.is_ready():
            raise ValidationError("SMTP 配置未完成，无法发送测试邮件")

        now = time_utils.now_china()
        subject = f"WhaleFall 测试邮件 - {now.strftime('%Y-%m-%d %H:%M:%S')}"
        body = "\n".join(
            [
                "这是一封来自 WhaleFall 的测试邮件。",
                "",
                f"发送时间: {now.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Shanghai)",
                f"发件人: {current_app.config.get('MAIL_FROM_ADDRESS') or '-'}",
                f"应用: {current_app.config.get('APP_NAME') or 'WhaleFall'}",
            ],
        )
        self._sender.send_email(
            recipients=normalized_recipients,
            subject=subject,
            text_body=body,
        )
        return {
            "sent": True,
            "recipient_count": len(normalized_recipients),
            "recipients": normalized_recipients,
        }

    @staticmethod
    def _is_smtp_ready() -> bool:
        host = str(current_app.config.get("MAIL_SMTP_HOST") or "").strip()
        from_address = str(current_app.config.get("MAIL_FROM_ADDRESS") or "").strip()
        username = str(current_app.config.get("MAIL_SMTP_USERNAME") or "").strip()
        password = str(current_app.config.get("MAIL_SMTP_PASSWORD") or "").strip()
        use_tls = bool(current_app.config.get("MAIL_USE_TLS"))
        use_ssl = bool(current_app.config.get("MAIL_USE_SSL"))
        if not host or not from_address:
            return False
        if use_tls and use_ssl:
            return False
        return not ((username and not password) or (password and not username))
