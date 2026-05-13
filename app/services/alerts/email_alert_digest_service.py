"""告警汇总投递服务."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.services.alerts.email_sender import EmailSender
from app.services.alerts.feishu_sender import FeishuSender
from app.utils.time_utils import time_utils

ALERT_TYPE_LABELS = {
    "database_capacity_growth": "数据库容量异常增长",
    "database_sync_failure": "数据库同步异常",
    "account_sync_failure": "账户同步异常",
    "privileged_account_discovery": "新增高权限账户",
    "backup_status_issue": "备份告警",
}
ALERT_RULES = (
    ("database_capacity_growth", "数据库容量异常增长", "database_capacity_enabled"),
    ("account_sync_failure", "账户同步异常", "account_sync_failure_enabled"),
    ("database_sync_failure", "数据库同步异常", "database_sync_failure_enabled"),
    ("privileged_account_discovery", "新增高权限账户", "privileged_account_enabled"),
    ("backup_status_issue", "备份告警", "backup_issue_enabled"),
)
EMAIL_CHANNEL = "email"
FEISHU_CHANNEL = "feishu"
DELIVERY_STEPS = {
    EMAIL_CHANNEL: ("deliver_email_digest", "发送汇总邮件"),
    FEISHU_CHANNEL: ("deliver_feishu_digest", "发送飞书通知"),
}


class EmailAlertDigestService:
    """告警汇总投递服务."""

    def __init__(
        self,
        repository: EmailAlertsRepository | Any | None = None,
        sender: EmailSender | Any | None = None,
        feishu_sender: FeishuSender | Any | None = None,
        settings_service: EmailAlertSettingsService | Any | None = None,
    ) -> None:
        """初始化告警汇总服务依赖."""
        self._repository = repository or EmailAlertsRepository()
        self._sender = sender or EmailSender()
        self._settings_service = settings_service or EmailAlertSettingsService()
        self._feishu_sender = feishu_sender or FeishuSender(settings_service=self._settings_service)

    def send_pending_digest(self, now: datetime | None = None) -> dict[str, Any]:
        """发送待汇总事件，并返回规则级与投递步骤的结构化结果."""
        resolved_now = now or time_utils.now()
        bucket_date = self._resolve_bucket_date(resolved_now)
        settings = self._settings_service.get_or_create_settings()
        recipients = list(settings.recipients_json or [])
        enabled_channels = self._resolve_enabled_channels(settings)
        pending_by_channel = {
            channel: self._repository.list_pending_digest_events(channel=channel) for channel in enabled_channels
        }
        events = self._unique_events([event for channel_events in pending_by_channel.values() for event in channel_events])
        bucket_stats = self._repository.get_bucket_event_counts(bucket_date, channels=enabled_channels)
        rule_results = self._build_rule_results(settings=settings, events=events, bucket_stats=bucket_stats)
        base_result = {
            "sent": False,
            "skipped": False,
            "skip_reason": None,
            "event_count": len(events),
            "recipient_count": len(recipients),
            "subject": None,
            "rule_results": rule_results,
            "delivery_steps": [],
        }

        if not enabled_channels:
            return self._with_delivery_steps(
                base_result,
                delivery_steps=self._build_disabled_delivery_steps(),
                skipped=True,
                skip_reason="no_delivery_channel",
            )

        if not events:
            sent_count = sum(item.get("sent_count", 0) for item in bucket_stats.values())
            return self._with_delivery_steps(
                base_result,
                delivery_steps=self._build_no_event_delivery_steps(
                    enabled_channels=enabled_channels,
                    disabled_channels=self._resolve_disabled_channels(enabled_channels),
                    sent_count=sent_count,
                    recipients=recipients,
                ),
                skipped=True,
                skip_reason="already_sent_today" if sent_count > 0 else "no_pending_events",
            )

        subject = f"告警汇总 - {self._format_subject_date(resolved_now)}"
        text_body = self._build_text_body(events)
        delivery_steps = [
            self._send_email_digest(
                events=pending_by_channel.get(EMAIL_CHANNEL, []),
                recipients=recipients,
                subject=subject,
                text_body=text_body,
                delivered_at=resolved_now,
            )
            if EMAIL_CHANNEL in enabled_channels
            else self._build_delivery_step(
                channel=EMAIL_CHANNEL,
                display_state="skipped_disabled",
                summary="邮件通道未启用",
            ),
            self._send_feishu_digest(
                events=pending_by_channel.get(FEISHU_CHANNEL, []),
                title=subject,
                text_body=text_body,
                delivered_at=resolved_now,
            )
            if FEISHU_CHANNEL in enabled_channels
            else self._build_delivery_step(
                channel=FEISHU_CHANNEL,
                display_state="skipped_disabled",
                summary="飞书通道未启用",
            ),
        ]
        sent = any(step.get("status") == "completed" and step.get("display_state") == "sent" for step in delivery_steps)
        failed_enabled_steps = [
            step
            for step in delivery_steps
            if step.get("status") == "failed" and step.get("item_key") in self._enabled_step_keys(enabled_channels)
        ]
        result = self._with_delivery_steps(
            base_result,
            delivery_steps=delivery_steps,
            skipped=not sent and not failed_enabled_steps,
            skip_reason=None,
        )
        return {
            **result,
            "sent": sent,
            "subject": subject,
            "failed": bool(failed_enabled_steps) and not sent,
        }

    def _send_email_digest(
        self,
        *,
        events: Sequence[Any],
        recipients: list[str],
        subject: str,
        text_body: str,
        delivered_at: datetime,
    ) -> dict[str, object]:
        if not events:
            return self._build_delivery_step(
                channel=EMAIL_CHANNEL,
                display_state="skipped_no_event",
                summary="无待发送邮件事件",
                skip_reason="no_pending_events",
                recipient_count=len(recipients),
            )
        event_ids = [int(event.id) for event in events]
        if not recipients:
            return self._build_delivery_step(
                channel=EMAIL_CHANNEL,
                display_state="skipped_no_recipients",
                summary="未配置收件人",
                skip_reason="no_recipients",
            )
        if not self._sender.is_ready():
            error_message = "SMTP 配置未完成"
            self._repository.record_digest_delivery(
                channel=EMAIL_CHANNEL,
                event_ids=event_ids,
                delivered_at=delivered_at,
                status="failed",
                error_message=error_message,
            )
            return self._build_delivery_step(
                channel=EMAIL_CHANNEL,
                status="failed",
                display_state="failed",
                summary=error_message,
                recipient_count=len(recipients),
                error_message=error_message,
            )
        try:
            self._sender.send_email(recipients=recipients, subject=subject, text_body=text_body)
        except Exception as exc:
            self._repository.record_digest_delivery(
                channel=EMAIL_CHANNEL,
                event_ids=event_ids,
                delivered_at=delivered_at,
                status="failed",
                error_message=str(exc),
            )
            return self._build_delivery_step(
                channel=EMAIL_CHANNEL,
                status="failed",
                display_state="failed",
                summary="发送汇总邮件失败",
                recipient_count=len(recipients),
                error_message=str(exc),
            )

        self._repository.record_digest_delivery(
            channel=EMAIL_CHANNEL,
            event_ids=event_ids,
            delivered_at=delivered_at,
            status="sent",
        )
        return self._build_delivery_step(
            channel=EMAIL_CHANNEL,
            display_state="sent",
            summary=f"已发送 {len(events)} 条事件到 {len(recipients)} 个收件人",
            recipient_count=len(recipients),
        )

    def _send_feishu_digest(
        self,
        *,
        events: Sequence[Any],
        title: str,
        text_body: str,
        delivered_at: datetime,
    ) -> dict[str, object]:
        if not events:
            return self._build_delivery_step(
                channel=FEISHU_CHANNEL,
                display_state="skipped_no_event",
                summary="无待发送飞书事件",
                skip_reason="no_pending_events",
            )
        event_ids = [int(event.id) for event in events]
        if not self._feishu_sender.is_ready():
            error_message = "飞书机器人 URL 未配置"
            self._repository.record_digest_delivery(
                channel=FEISHU_CHANNEL,
                event_ids=event_ids,
                delivered_at=delivered_at,
                status="failed",
                error_message=error_message,
            )
            return self._build_delivery_step(
                channel=FEISHU_CHANNEL,
                status="failed",
                display_state="failed",
                summary=error_message,
                error_message=error_message,
            )
        try:
            self._feishu_sender.send_text(title=title, text_body=text_body)
        except Exception as exc:
            self._repository.record_digest_delivery(
                channel=FEISHU_CHANNEL,
                event_ids=event_ids,
                delivered_at=delivered_at,
                status="failed",
                error_message=str(exc),
            )
            return self._build_delivery_step(
                channel=FEISHU_CHANNEL,
                status="failed",
                display_state="failed",
                summary="发送飞书通知失败",
                error_message=str(exc),
            )

        self._repository.record_digest_delivery(
            channel=FEISHU_CHANNEL,
            event_ids=event_ids,
            delivered_at=delivered_at,
            status="sent",
        )
        return self._build_delivery_step(
            channel=FEISHU_CHANNEL,
            display_state="sent",
            summary=f"已发送 {len(events)} 条事件到飞书",
        )

    @staticmethod
    def _resolve_enabled_channels(settings: object) -> list[str]:
        channels: list[str] = []
        if bool(getattr(settings, "global_enabled", False)):
            channels.append(EMAIL_CHANNEL)
        if bool(getattr(settings, "feishu_enabled", False)):
            channels.append(FEISHU_CHANNEL)
        return channels

    @staticmethod
    def _resolve_disabled_channels(enabled_channels: list[str]) -> list[str]:
        return [channel for channel in (EMAIL_CHANNEL, FEISHU_CHANNEL) if channel not in enabled_channels]

    @staticmethod
    def _enabled_step_keys(enabled_channels: list[str]) -> set[str]:
        return {DELIVERY_STEPS[channel][0] for channel in enabled_channels}

    @staticmethod
    def _unique_events(events: Sequence[Any]) -> list[Any]:
        seen: set[int] = set()
        unique_events: list[Any] = []
        for event in events:
            event_id = int(event.id)
            if event_id in seen:
                continue
            seen.add(event_id)
            unique_events.append(event)
        return unique_events

    def _build_disabled_delivery_steps(self) -> list[dict[str, object]]:
        return [
            self._build_delivery_step(channel=EMAIL_CHANNEL, display_state="skipped_disabled", summary="邮件通道未启用"),
            self._build_delivery_step(channel=FEISHU_CHANNEL, display_state="skipped_disabled", summary="飞书通道未启用"),
        ]

    def _build_no_event_delivery_steps(
        self,
        *,
        enabled_channels: list[str],
        disabled_channels: list[str],
        sent_count: int,
        recipients: list[str],
    ) -> list[dict[str, object]]:
        display_state = "skipped_already_sent" if sent_count > 0 else "skipped_no_event"
        summary = f"当天已发送 {sent_count} 条告警事件，本次无待发送事件" if sent_count > 0 else "无待发送事件"
        steps = [
            self._build_delivery_step(
                channel=channel,
                display_state=display_state,
                summary=summary,
                skip_reason="already_sent_today" if sent_count > 0 else "no_pending_events",
                recipient_count=len(recipients) if channel == EMAIL_CHANNEL else 0,
            )
            for channel in enabled_channels
        ]
        steps.extend(
            self._build_delivery_step(
                channel=channel,
                display_state="skipped_disabled",
                summary=f"{'邮件' if channel == EMAIL_CHANNEL else '飞书'}通道未启用",
            )
            for channel in disabled_channels
        )
        return steps

    @staticmethod
    def _with_delivery_steps(
        base_result: dict[str, object],
        *,
        delivery_steps: list[dict[str, object]],
        skipped: bool,
        skip_reason: str | None,
    ) -> dict[str, object]:
        primary_step = next(
            (step for step in delivery_steps if step.get("item_key") == DELIVERY_STEPS[EMAIL_CHANNEL][0]),
            None,
        )
        if primary_step is None and delivery_steps:
            primary_step = delivery_steps[0]
        return {
            **base_result,
            "skipped": skipped,
            "skip_reason": skip_reason,
            "delivery_steps": delivery_steps,
            "send_step": primary_step,
        }

    @staticmethod
    def _build_delivery_step(
        *,
        channel: str,
        display_state: str,
        summary: str,
        status: str = "completed",
        recipient_count: int = 0,
        skip_reason: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, object]:
        item_key, item_name = DELIVERY_STEPS[channel]
        return {
            "item_key": item_key,
            "item_name": item_name,
            "status": status,
            "display_state": display_state,
            "summary": summary,
            "skip_reason": skip_reason,
            "recipient_count": recipient_count,
            "error_message": error_message,
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

        lines = ["WhaleFall 每日告警汇总", ""]
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
        if alert_type == "backup_status_issue":
            return f"{payload.get('instance_name')} - {payload.get('reason_text')}"
        return str(payload)

    @staticmethod
    def _build_rule_results(
        *,
        settings: object,
        events: Sequence[Any],
        bucket_stats: dict[str, dict[str, int]],
    ) -> list[dict[str, object]]:
        pending_counts: dict[str, int] = defaultdict(int)
        for event in events:
            pending_counts[str(getattr(event, "alert_type", ""))] += 1

        results: list[dict[str, object]] = []
        for item_key, item_name, flag_name in ALERT_RULES:
            enabled = bool(getattr(settings, flag_name, False))
            pending_count = int(pending_counts.get(item_key, 0))
            sent_count = int(bucket_stats.get(item_key, {}).get("sent_count", 0))
            display_state = "disabled"
            summary = "规则未启用"
            if enabled:
                if pending_count > 0:
                    display_state = "pending"
                    summary = f"待发送事件 {pending_count} 条"
                elif sent_count > 0:
                    display_state = "already_sent"
                    summary = f"当天已发送 {sent_count} 条，本次待发送 0 条"
                else:
                    display_state = "no_event"
                    summary = "当天未产生事件"
            elif pending_count > 0:
                summary = f"规则未启用，累计待发送事件 {pending_count} 条"
            elif sent_count > 0:
                summary = f"规则未启用，当天已发送 {sent_count} 条"
            results.append(
                {
                    "item_key": item_key,
                    "item_name": item_name,
                    "enabled": enabled,
                    "pending_count": pending_count,
                    "sent_count": sent_count,
                    "display_state": display_state,
                    "summary": summary,
                },
            )
        return results

    @staticmethod
    def _resolve_bucket_date(now: datetime):
        china_time = time_utils.to_china(now)
        if china_time is None:
            return time_utils.now_china().date()
        return china_time.date()
