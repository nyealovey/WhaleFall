"""邮件告警服务集合."""

from app.services.alerts.email_alert_digest_service import EmailAlertDigestService
from app.services.alerts.email_alert_event_service import EmailAlertEventService
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.services.alerts.email_sender import EmailSender

__all__ = [
    "EmailAlertDigestService",
    "EmailAlertEventService",
    "EmailAlertSettingsService",
    "EmailSender",
]
