from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
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
    feishu_enabled: bool = False
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
        self.delivery_records: list[tuple[str, list[int], datetime, str, str | None]] = []
        self.daily_stats = daily_stats or {}
        self.list_calls: list[dict[str, object]] = []

    def list_pending_digest_events(
        self,
        channel: str | None = None,
        bucket_date: date | None = None,
    ) -> list[_DummyEvent]:
        self.list_calls.append({"channel": channel, "bucket_date": bucket_date})
        return list(self.events)

    def mark_events_digest_sent(self, event_ids: list[int], sent_at: datetime) -> None:
        self.marked.append((list(event_ids), sent_at))

    def get_bucket_event_counts(self, bucket_date, channels: list[str] | None = None) -> dict[str, dict[str, int]]:
        _ = (bucket_date, channels)
        return {
            alert_type: {
                "pending_count": int(values.get("pending_count", 0)),
                "sent_count": int(values.get("sent_count", 0)),
            }
            for alert_type, values in self.daily_stats.items()
        }

    def record_digest_delivery(
        self,
        *,
        channel: str,
        event_ids: list[int],
        delivered_at: datetime,
        status: str,
        error_message: str | None = None,
    ) -> None:
        self.delivery_records.append((channel, list(event_ids), delivered_at, status, error_message))
        if channel == "email" and status == "sent":
            self.mark_events_digest_sent(event_ids, delivered_at)


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
    def __init__(self, *, ready: bool = True, should_fail: bool = False) -> None:
        self.ready = ready
        self.should_fail = should_fail
        self.calls: list[dict[str, object]] = []

    def is_ready(self) -> bool:
        return self.ready

    def send_text(self, *, title: str, text_body: str) -> None:
        self.calls.append({"title": title, "text_body": text_body})
        if self.should_fail:
            raise RuntimeError("飞书发送失败")


class _StubSettingsService:
    def __init__(self, settings: _DummySettings) -> None:
        self.settings = settings

    def get_or_create_settings(self) -> _DummySettings:
        return self.settings

    def get_feishu_webhook_url(self) -> str:
        return "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"


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
        "item_key": "deliver_email_digest",
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
    assert "告警汇总" in str(sender.calls[0]["subject"])
    assert "orders" in str(sender.calls[0]["text_body"])
    assert repository.marked == [([1, 2], datetime(2026, 3, 17, 9, 0, tzinfo=UTC))]


@pytest.mark.unit
def test_email_alert_digest_service_records_email_and_feishu_delivery_independently() -> None:
    settings = _DummySettings(
        global_enabled=True,
        recipients_json=["ops@example.com"],
        feishu_enabled=True,
        database_sync_failure_enabled=True,
    )
    events = [
        _DummyEvent(
            id=7,
            alert_type="database_sync_failure",
            payload_json={"instance_name": "prod-mysql-1", "error_message": "连接失败"},
            occurred_at=datetime(2026, 3, 17, 2, 0, tzinfo=UTC),
        ),
    ]
    repository = _StubRepository(events)
    email_sender = _StubSender()
    feishu_sender = _StubFeishuSender(should_fail=True)
    service = EmailAlertDigestService(
        repository=cast(EmailAlertsRepository, repository),
        sender=cast(EmailSender, email_sender),
        feishu_sender=feishu_sender,
        settings_service=cast(EmailAlertSettingsService, _StubSettingsService(settings)),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 9, 0, tzinfo=UTC))

    assert summary["sent"] is True
    assert email_sender.calls
    assert feishu_sender.calls
    assert summary["delivery_steps"] == [
        {
            "item_key": "deliver_email_digest",
            "item_name": "发送汇总邮件",
            "status": "completed",
            "display_state": "sent",
            "summary": "已发送 1 条事件到 1 个收件人",
            "skip_reason": None,
            "recipient_count": 1,
            "error_message": None,
        },
        {
            "item_key": "deliver_feishu_digest",
            "item_name": "发送飞书通知",
            "status": "failed",
            "display_state": "failed",
            "summary": "发送飞书通知失败",
            "skip_reason": None,
            "recipient_count": 0,
            "error_message": "飞书发送失败",
        },
    ]
    assert repository.delivery_records == [
        ("email", [7], datetime(2026, 3, 17, 9, 0, tzinfo=UTC), "sent", None),
        ("feishu", [7], datetime(2026, 3, 17, 9, 0, tzinfo=UTC), "failed", "飞书发送失败"),
    ]


@pytest.mark.unit
def test_email_alert_digest_service_only_sends_events_from_current_bucket_date() -> None:
    class _BucketAwareRepository(_StubRepository):
        def __init__(self, current_events: list[_DummyEvent], historical_events: list[_DummyEvent]) -> None:
            super().__init__(current_events + historical_events)
            self.current_events = current_events
            self.historical_events = historical_events

        def list_pending_digest_events(
            self,
            channel: str | None = None,
            bucket_date: date | None = None,
        ) -> list[_DummyEvent]:
            self.list_calls.append({"channel": channel, "bucket_date": bucket_date})
            if bucket_date == date(2026, 3, 17):
                return list(self.current_events)
            return list(self.current_events + self.historical_events)

    settings = _DummySettings(global_enabled=True, recipients_json=["ops@example.com"], backup_issue_enabled=True)
    current_events = [
        _DummyEvent(
            id=10,
            alert_type="backup_status_issue",
            payload_json={"instance_name": "today-db", "reason_text": "当天没有备份"},
            occurred_at=datetime(2026, 3, 17, 1, 0, tzinfo=UTC),
        ),
    ]
    historical_events = [
        _DummyEvent(
            id=9,
            alert_type="backup_status_issue",
            payload_json={"instance_name": "old-db", "reason_text": "备份异常（最近备份超过24小时）"},
            occurred_at=datetime(2026, 3, 16, 1, 0, tzinfo=UTC),
        ),
    ]
    repository = _BucketAwareRepository(current_events, historical_events)
    sender = _StubSender()
    service = EmailAlertDigestService(
        repository=cast(EmailAlertsRepository, repository),
        sender=cast(EmailSender, sender),
        settings_service=cast(EmailAlertSettingsService, _StubSettingsService(settings)),
    )

    summary = service.send_pending_digest(now=datetime(2026, 3, 17, 9, 0, tzinfo=UTC))

    assert repository.list_calls == [{"channel": "email", "bucket_date": date(2026, 3, 17)}]
    assert summary["event_count"] == 1
    assert repository.marked == [([10], datetime(2026, 3, 17, 9, 0, tzinfo=UTC))]
    text_body = str(sender.calls[0]["text_body"])
    assert "today-db - 当天没有备份" in text_body
    assert "old-db" not in text_body


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
        "item_key": "deliver_email_digest",
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
        "item_key": "deliver_email_digest",
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
