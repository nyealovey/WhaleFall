from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from app.services.alerts.email_alert_event_service import EmailAlertEventService


@dataclass(slots=True)
class _DummySettings:
    global_enabled: bool = True
    database_capacity_enabled: bool = True
    database_capacity_percent_threshold: int = 30
    database_capacity_absolute_gb_threshold: int = 20


@dataclass(slots=True)
class _DummyBaseline:
    size_mb: int
    collected_date: date


class _StubRepository:
    def __init__(self, baselines: dict[tuple[int, str], _DummyBaseline | None]) -> None:
        self.baselines = baselines
        self.created_events: list[dict[str, object]] = []

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
