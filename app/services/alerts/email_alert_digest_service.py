"""邮件告警汇总发送服务."""

from __future__ import annotations

from collections.abc import Sequence
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.services.alerts.email_sender import EmailSender
from app.utils.time_utils import time_utils

ALERT_TYPE_LABELS = {
    "database_capacity_growth": "数据库容量异常增长",
    "database_sync_failure": "数据库同步异常",
    "account_sync_failure": "账户同步异常",
    "privileged_account_discovery": "新增高权限账户",
}


class EmailAlertDigestService:
    """邮件告警汇总发送服务."""

    def __init__(
        self,
        repository: EmailAlertsRepository | None = None,
        sender: EmailSender | None = None,
        settings_service: EmailAlertSettingsService | None = None,
    ) -> None:
        self._repository = repository or EmailAlertsRepository()
        self._sender = sender or EmailSender()
        self._settings_service = settings_service or EmailAlertSettingsService()

    def send_pending_digest(self, now: datetime | None = None) -> dict[str, object]:
        settings = self._settings_service.get_or_create_settings()
        recipients = list(settings.recipients_json or [])
        if not bool(settings.global_enabled):
            return {"sent": False, "skipped": True, "skip_reason": "global_disabled", "event_count": 0}
        if not recipients:
            return {"sent": False, "skipped": True, "skip_reason": "no_recipients", "event_count": 0}

        events = self._repository.list_pending_digest_events()
        if not events:
            return {"sent": False, "skipped": True, "skip_reason": "no_pending_events", "event_count": 0}
        if not self._sender.is_ready():
            raise RuntimeError("SMTP 配置未完成")

        resolved_now = now or time_utils.now()
        subject = f"邮件告警汇总 - {self._format_subject_date(resolved_now)}"
        text_body = self._build_text_body(events)
        self._sender.send_email(recipients=recipients, subject=subject, text_body=text_body)
        event_ids = [int(event.id) for event in events]
        self._repository.mark_events_digest_sent(event_ids, resolved_now)
        return {
            "sent": True,
            "skipped": False,
            "event_count": len(events),
            "recipient_count": len(recipients),
            "subject": subject,
        }

    @staticmethod
    def _format_subject_date(now: datetime) -> str:
        china_time = time_utils.to_china(now)
        if china_time is None:
            china_time = time_utils.now_china()
        return china_time.strftime("%Y-%m-%d")

    def _build_text_body(self, events: Sequence[Any]) -> str:
        grouped: dict[str, list[Any]] = defaultdict(list)
        for event in events:
            grouped[str(event.alert_type)].append(event)

        lines = ["WhaleFall 每日邮件告警汇总", ""]
        for alert_type, typed_events in grouped.items():
            lines.append(f"[{ALERT_TYPE_LABELS.get(alert_type, alert_type)}] {len(typed_events)} 条")
            for event in typed_events:
                payload = getattr(event, "payload_json", {}) or {}
                lines.append(f"- {self._render_event_line(alert_type, payload)}")
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    def _render_event_line(alert_type: str, payload: dict[str, object]) -> str:
        if alert_type == "database_capacity_growth":
            return (
                f"{payload.get('instance_name')} / {payload.get('database_name')} "
                f"增长 {payload.get('size_change_percent')}%"
            )
        if alert_type in {"database_sync_failure", "account_sync_failure"}:
            return f"{payload.get('instance_name')} - {payload.get('error_message')}"
        if alert_type == "privileged_account_discovery":
            return f"{payload.get('instance_name')} / {payload.get('username')} - {payload.get('reason')}"
        return str(payload)
