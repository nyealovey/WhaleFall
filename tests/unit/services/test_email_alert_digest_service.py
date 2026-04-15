from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

import pytest

from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.services.alerts.email_alert_digest_service import EmailAlertDigestService
from app.services.alerts.email_alert_settings_service import EmailAlertSettingsService
from app.services.alerts.email_sender import EmailSender


@dataclass(slots=True)
class _DummySettings:
    global_enabled: bool = True
    recipients_json: list[str] = None  # type: ignore[assignment]
    database_capacity_enabled: bool = False
    account_sync_failure_enabled: bool = False
    database_sync_failure_enabled: bool = False
    privileged_account_enabled: bool = False
    backup_issue_enabled: bool = False


@dataclass(slots=True)
class _DummyEvent:
    id: int
    alert_type: str
    payload_json: dict[str, object]
    occurred_at: datetime


class _StubRepository:
    def __init__(
        self,
        events: list[_DummyEvent],
        *,
        daily_stats: dict[str, dict[str, int]] | None = None,
    ) -> None:
        self.events = events
        self.marked: list[tuple[list[int], datetime]] = []
        self.daily_stats = daily_stats or {}

    def list_pending_digest_events(self) -> list[_DummyEvent]:
        return list(self.events)

    def mark_events_digest_sent(self, event_ids: list[int], sent_at: datetime) -> None:
        self.marked.append((list(event_ids), sent_at))

    def get_bucket_event_counts(self, bucket_date) -> dict[str, dict[str, int]]:
        _ = bucket_date
        return {
            alert_type: {
                "pending_count": int(values.get("pending_count", 0)),
                "sent_count": int(values.get("sent_count", 0)),
            }
            for alert_type, values in self.daily_stats.items()
        }


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
        repository=cast(EmailAlertsRepository, repository),
        sender=cast(EmailSender, sender),
        settings_service=cast(EmailAlertSettingsService, _StubSettingsService(settings)),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 9, 0, tzinfo=UTC))

    assert summary["sent"] is True
    assert summary["event_count"] == 2
    assert summary["rule_results"] == [
        {
            "item_key": "database_capacity_growth",
            "item_name": "数据库容量异常增长",
            "enabled": False,
            "pending_count": 1,
            "sent_count": 0,
            "display_state": "disabled",
            "summary": "规则未启用，累计待发送事件 1 条",
        },
        {
            "item_key": "account_sync_failure",
            "item_name": "账户同步异常",
            "enabled": False,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "disabled",
            "summary": "规则未启用",
        },
        {
            "item_key": "database_sync_failure",
            "item_name": "数据库同步异常",
            "enabled": False,
            "pending_count": 1,
            "sent_count": 0,
            "display_state": "disabled",
            "summary": "规则未启用，累计待发送事件 1 条",
        },
        {
            "item_key": "privileged_account_discovery",
            "item_name": "新增高权限账户",
            "enabled": False,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "disabled",
            "summary": "规则未启用",
        },
        {
            "item_key": "backup_status_issue",
            "item_name": "备份告警",
            "enabled": False,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "disabled",
            "summary": "规则未启用",
        },
    ]
    assert summary["send_step"] == {
        "item_key": "deliver_digest",
        "item_name": "发送汇总邮件",
        "status": "completed",
        "display_state": "sent",
        "summary": "已发送 2 条事件到 1 个收件人",
        "skip_reason": None,
        "recipient_count": 1,
        "error_message": None,
    }
    assert sender.calls
    assert sender.calls[0]["recipients"] == ["ops@example.com"]
    assert "邮件告警汇总" in str(sender.calls[0]["subject"])
    assert "orders" in str(sender.calls[0]["text_body"])
    assert repository.marked == [([1, 2], datetime(2026, 3, 17, 9, 0, tzinfo=UTC))]


@pytest.mark.unit
def test_email_alert_digest_service_reports_skip_structure_when_no_pending_events() -> None:
    settings = _DummySettings(
        global_enabled=True,
        recipients_json=["ops@example.com"],
        database_capacity_enabled=True,
        account_sync_failure_enabled=True,
        database_sync_failure_enabled=True,
        privileged_account_enabled=True,
        backup_issue_enabled=True,
    )
    service = EmailAlertDigestService(
        repository=cast(EmailAlertsRepository, _StubRepository([])),
        sender=cast(EmailSender, _StubSender()),
        settings_service=cast(EmailAlertSettingsService, _StubSettingsService(settings)),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 9, 0, tzinfo=UTC))

    assert summary["sent"] is False
    assert summary["skipped"] is True
    assert summary["skip_reason"] == "no_pending_events"
    assert summary["event_count"] == 0
    assert summary["send_step"] == {
        "item_key": "deliver_digest",
        "item_name": "发送汇总邮件",
        "status": "completed",
        "summary": "无待发送事件",
        "display_state": "skipped_no_event",
        "skip_reason": "no_pending_events",
        "recipient_count": 1,
        "error_message": None,
    }
    assert summary["rule_results"] == [
        {
            "item_key": "database_capacity_growth",
            "item_name": "数据库容量异常增长",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
        {
            "item_key": "account_sync_failure",
            "item_name": "账户同步异常",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
        {
            "item_key": "database_sync_failure",
            "item_name": "数据库同步异常",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
        {
            "item_key": "privileged_account_discovery",
            "item_name": "新增高权限账户",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
        {
            "item_key": "backup_status_issue",
            "item_name": "备份告警",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
    ]


@pytest.mark.unit
def test_email_alert_digest_service_distinguishes_already_sent_from_no_event() -> None:
    settings = _DummySettings(
        global_enabled=True,
        recipients_json=["ops@example.com"],
        database_capacity_enabled=True,
        account_sync_failure_enabled=True,
        database_sync_failure_enabled=True,
        privileged_account_enabled=True,
        backup_issue_enabled=True,
    )
    repository = _StubRepository(
        [],
        daily_stats={
            "database_sync_failure": {"pending_count": 0, "sent_count": 2},
            "account_sync_failure": {"pending_count": 0, "sent_count": 1},
        },
    )
    service = EmailAlertDigestService(
        repository=cast(EmailAlertsRepository, repository),
        sender=cast(EmailSender, _StubSender()),
        settings_service=cast(EmailAlertSettingsService, _StubSettingsService(settings)),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 11, 3, tzinfo=UTC))

    assert summary["sent"] is False
    assert summary["skipped"] is True
    assert summary["skip_reason"] == "already_sent_today"
    assert summary["send_step"] == {
        "item_key": "deliver_digest",
        "item_name": "发送汇总邮件",
        "status": "completed",
        "summary": "当天已发送 3 条告警事件，本次无待发送事件",
        "display_state": "skipped_already_sent",
        "skip_reason": "already_sent_today",
        "recipient_count": 1,
        "error_message": None,
    }
    assert summary["rule_results"] == [
        {
            "item_key": "database_capacity_growth",
            "item_name": "数据库容量异常增长",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
        {
            "item_key": "account_sync_failure",
            "item_name": "账户同步异常",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 1,
            "display_state": "already_sent",
            "summary": "当天已发送 1 条，本次待发送 0 条",
        },
        {
            "item_key": "database_sync_failure",
            "item_name": "数据库同步异常",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 2,
            "display_state": "already_sent",
            "summary": "当天已发送 2 条，本次待发送 0 条",
        },
        {
            "item_key": "privileged_account_discovery",
            "item_name": "新增高权限账户",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
        {
            "item_key": "backup_status_issue",
            "item_name": "备份告警",
            "enabled": True,
            "pending_count": 0,
            "sent_count": 0,
            "display_state": "no_event",
            "summary": "当天未产生事件",
        },
    ]


@pytest.mark.unit
def test_email_alert_digest_service_renders_backup_issue_events() -> None:
    settings = _DummySettings(global_enabled=True, recipients_json=["ops@example.com"], backup_issue_enabled=True)
    events = [
        _DummyEvent(
            id=3,
            alert_type="backup_status_issue",
            payload_json={
                "instance_name": "sqlserver-prod-1",
                "reason_text": "当天没有备份",
            },
            occurred_at=datetime(2026, 3, 17, 3, 0, tzinfo=UTC),
        ),
        _DummyEvent(
            id=4,
            alert_type="backup_status_issue",
            payload_json={
                "instance_name": "sqlserver-prod-2",
                "reason_text": "备份异常（最近备份超过24小时）",
            },
            occurred_at=datetime(2026, 3, 17, 4, 0, tzinfo=UTC),
        ),
    ]
    repository = _StubRepository(events)
    sender = _StubSender()
    service = EmailAlertDigestService(
        repository=cast(EmailAlertsRepository, repository),
        sender=cast(EmailSender, sender),
        settings_service=cast(EmailAlertSettingsService, _StubSettingsService(settings)),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 9, 0, tzinfo=UTC))

    assert summary["sent"] is True
    assert summary["rule_results"][-1] == {
        "item_key": "backup_status_issue",
        "item_name": "备份告警",
        "enabled": True,
        "pending_count": 2,
        "sent_count": 0,
        "display_state": "pending",
        "summary": "待发送事件 2 条",
    }
    assert sender.calls
    assert "sqlserver-prod-1 - 当天没有备份" in str(sender.calls[0]["text_body"])
    assert "sqlserver-prod-2 - 备份异常（最近备份超过24小时）" in str(sender.calls[0]["text_body"])
