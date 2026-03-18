"""邮件告警汇总发送服务."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
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
ALERT_RULES = (
    ("database_capacity_growth", "数据库容量异常增长", "database_capacity_enabled"),
    ("account_sync_failure", "账户同步异常", "account_sync_failure_enabled"),
    ("database_sync_failure", "数据库同步异常", "database_sync_failure_enabled"),
    ("privileged_account_discovery", "新增高权限账户", "privileged_account_enabled"),
)
SEND_STEP_ITEM_KEY = "deliver_digest"
SEND_STEP_ITEM_NAME = "发送汇总邮件"


class EmailAlertDigestService:
    """邮件告警汇总发送服务."""

    def __init__(
        self,
        repository: EmailAlertsRepository | None = None,
        sender: EmailSender | None = None,
        settings_service: EmailAlertSettingsService | None = None,
    ) -> None:
        """初始化邮件告警汇总服务依赖."""
        self._repository = repository or EmailAlertsRepository()
        self._sender = sender or EmailSender()
        self._settings_service = settings_service or EmailAlertSettingsService()

    def send_pending_digest(self, now: datetime | None = None) -> dict[str, object]:
        """发送待汇总事件，并返回规则级与发送步骤的结构化结果."""
        settings = self._settings_service.get_or_create_settings()
        recipients = list(settings.recipients_json or [])
        events = self._repository.list_pending_digest_events()
        rule_results = self._build_rule_results(settings=settings, events=events)
        base_result = {
            "sent": False,
            "skipped": False,
            "skip_reason": None,
            "event_count": len(events),
            "recipient_count": len(recipients),
            "subject": None,
            "rule_results": rule_results,
        }

        if not bool(settings.global_enabled):
            return {
                **base_result,
                "skipped": True,
                "skip_reason": "global_disabled",
                "send_step": self._build_send_step(
                    status="completed",
                    summary="总开关已关闭",
                    skip_reason="global_disabled",
                    recipient_count=len(recipients),
                ),
            }
        if not recipients:
            return {
                **base_result,
                "skipped": True,
                "skip_reason": "no_recipients",
                "send_step": self._build_send_step(
                    status="completed",
                    summary="未配置收件人",
                    skip_reason="no_recipients",
                    recipient_count=0,
                ),
            }
        if not events:
            return {
                **base_result,
                "skipped": True,
                "skip_reason": "no_pending_events",
                "send_step": self._build_send_step(
                    status="completed",
                    summary="无待发送事件",
                    skip_reason="no_pending_events",
                    recipient_count=len(recipients),
                ),
            }
        if not self._sender.is_ready():
            return {
                **base_result,
                "send_step": self._build_send_step(
                    status="failed",
                    summary="SMTP 配置未完成",
                    recipient_count=len(recipients),
                    error_message="SMTP 配置未完成",
                ),
            }

        resolved_now = now or time_utils.now()
        subject = f"邮件告警汇总 - {self._format_subject_date(resolved_now)}"
        text_body = self._build_text_body(events)
        try:
            self._sender.send_email(recipients=recipients, subject=subject, text_body=text_body)
        except Exception as exc:
            return {
                **base_result,
                "subject": subject,
                "send_step": self._build_send_step(
                    status="failed",
                    summary="发送汇总邮件失败",
                    recipient_count=len(recipients),
                    error_message=str(exc),
                ),
            }
        event_ids = [int(event.id) for event in events]
        self._repository.mark_events_digest_sent(event_ids, resolved_now)
        return {
            **base_result,
            "sent": True,
            "subject": subject,
            "send_step": self._build_send_step(
                status="completed",
                summary=f"已发送 {len(events)} 条事件到 {len(recipients)} 个收件人",
                recipient_count=len(recipients),
            ),
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

    @staticmethod
    def _build_send_step(
        *,
        status: str,
        summary: str,
        recipient_count: int,
        skip_reason: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, object]:
        return {
            "item_key": SEND_STEP_ITEM_KEY,
            "item_name": SEND_STEP_ITEM_NAME,
            "status": status,
            "summary": summary,
            "skip_reason": skip_reason,
            "recipient_count": recipient_count,
            "error_message": error_message,
        }

    @staticmethod
    def _build_rule_results(*, settings: object, events: Sequence[Any]) -> list[dict[str, object]]:
        event_counts: dict[str, int] = defaultdict(int)
        for event in events:
            event_counts[str(getattr(event, "alert_type", ""))] += 1

        results: list[dict[str, object]] = []
        for item_key, item_name, flag_name in ALERT_RULES:
            enabled = bool(getattr(settings, flag_name, False))
            event_count = int(event_counts.get(item_key, 0))
            summary = "规则未启用"
            if enabled:
                summary = f"待发送事件 {event_count} 条"
            elif event_count > 0:
                summary = f"规则未启用，累计待发送事件 {event_count} 条"
            results.append(
                {
                    "item_key": item_key,
                    "item_name": item_name,
                    "enabled": enabled,
                    "event_count": event_count,
                    "summary": summary,
                },
            )
        return results
