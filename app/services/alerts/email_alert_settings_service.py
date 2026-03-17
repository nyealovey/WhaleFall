"""邮件告警配置服务."""

from __future__ import annotations

from typing import Any, cast

from flask import current_app

from app import db
from app.models.email_alert_setting import EmailAlertSetting
from app.repositories.email_alerts_repository import EmailAlertsRepository


class EmailAlertSettingsService:
    """邮件告警配置服务."""

    def __init__(self, repository: EmailAlertsRepository | None = None) -> None:
        self._repository = repository or EmailAlertsRepository()

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
