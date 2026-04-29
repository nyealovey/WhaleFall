from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.services.alerts.email_alert_event_service import EmailAlertEventService


@dataclass(slots=True)
class _DummySettings:
    global_enabled: bool = True
    database_capacity_enabled: bool = True
    database_capacity_percent_threshold: int = 30
    database_capacity_absolute_gb_threshold: int = 20
    backup_issue_enabled: bool = True


@dataclass(slots=True)
class _DummyBaseline:
    size_mb: int
    collected_date: date


class _StubRepository:
    def __init__(self, baselines: dict[tuple[int, str], _DummyBaseline | None]) -> None:
        self.baselines = baselines
        self.created_events: list[dict[str, Any]] = []

    def find_recent_database_baseline(
        self,
        *,
        instance_id: int,
        database_name: str,
        current_collected_date: date,
        lookback_days: int,
    ) -> _DummyBaseline | None:
        _ = (current_collected_date, lookback_days)
        return self.baselines.get((instance_id, database_name))

    def create_event(self, **payload: object) -> None:
        self.created_events.append(dict(payload))

    def upsert_backup_issue_event(self, **payload: object) -> bool:
        self.created_events.append(dict(payload))
        return True

    def delete_pending_backup_issue_events_not_in(self, *, bucket_date, dedupe_keys: set[str]) -> int:
        _ = (bucket_date, dedupe_keys)
        return 0


class _StubSettingsService:
    def __init__(self, settings: _DummySettings) -> None:
        self.settings = settings

    def get_or_create_settings(self) -> _DummySettings:
        return self.settings


@pytest.mark.unit
def test_email_alert_event_service_uses_recent_baseline_within_three_days() -> None:
    repository = _StubRepository(
        baselines={
            (1, "orders"): _DummyBaseline(size_mb=100 * 1024, collected_date=date(2026, 3, 15)),
        },
    )
    service = EmailAlertEventService(
        repository=repository,
        settings_service=_StubSettingsService(_DummySettings()),
    )

    created = service.record_database_capacity_events(
        current_rows=[
            {
                "instance_id": 1,
                "instance_name": "prod-mysql-1",
                "database_name": "orders",
                "size_mb": 145 * 1024,
                "collected_date": date(2026, 3, 17),
            },
        ],
        occurred_at=datetime(2026, 3, 17, 3, 0, tzinfo=UTC),
    )

    assert created == 1
    assert len(repository.created_events) == 1
    payload = repository.created_events[0]
    assert payload["alert_type"] == "database_capacity_growth"
    assert payload["dedupe_key"] == "1:orders"
    body = payload["payload_json"]
    assert isinstance(body, dict)
    assert body["baseline_collected_date"] == "2026-03-15"
    assert body["baseline_age_days"] == 2
    assert body["size_change_percent"] == 45.0


@pytest.mark.unit
def test_email_alert_event_service_skips_capacity_alert_without_recent_baseline() -> None:
    repository = _StubRepository(baselines={(1, "orders"): None})
    service = EmailAlertEventService(
        repository=repository,
        settings_service=_StubSettingsService(_DummySettings()),
    )

    created = service.record_database_capacity_events(
        current_rows=[
            {
                "instance_id": 1,
                "instance_name": "prod-mysql-1",
                "database_name": "orders",
                "size_mb": 145 * 1024,
                "collected_date": date(2026, 3, 17),
            },
        ],
        occurred_at=datetime(2026, 3, 17, 3, 0, tzinfo=UTC),
    )

    assert created == 0
    assert repository.created_events == []


@pytest.mark.unit
def test_email_alert_event_service_records_backup_issue_events_for_not_backed_up_and_stale_instances() -> None:
    repository = _StubRepository(baselines={})
    service = EmailAlertEventService(
        repository=repository,
        settings_service=_StubSettingsService(_DummySettings()),
    )

    created = service.record_backup_issue_events(
        backup_rows=[
            {
                "instance_id": 1,
                "instance_name": "sqlserver-prod-1",
                "backup_status": "not_backed_up",
                "backup_last_time": None,
            },
            {
                "instance_id": 2,
                "instance_name": "sqlserver-prod-2",
                "backup_status": "backup_stale",
                "backup_last_time": "2026-03-15T03:00:00+00:00",
            },
            {
                "instance_id": 3,
                "instance_name": "sqlserver-prod-3",
                "backup_status": "backed_up",
                "backup_last_time": "2026-03-17T03:00:00+00:00",
            },
        ],
        occurred_at=datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
    )

    assert created == 2
    assert [event["dedupe_key"] for event in repository.created_events] == ["1", "2"]
    assert repository.created_events[0]["alert_type"] == "backup_status_issue"
    assert repository.created_events[0]["payload_json"]["reason_text"] == "当天没有备份"
    assert repository.created_events[1]["payload_json"]["reason_text"] == "备份异常（最近备份超过24小时）"
