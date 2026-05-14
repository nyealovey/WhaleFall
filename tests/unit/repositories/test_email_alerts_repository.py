from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from app import create_app, db
from app.models.email_alert_event import EmailAlertEvent
from app.repositories.email_alerts_repository import EmailAlertsRepository
from app.settings import Settings


@pytest.fixture(scope="function")
def app(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("CACHE_TYPE", "simple")
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)

    app = create_app(init_scheduler_on_start=False, settings=Settings.load())
    app.config["TESTING"] = True
    return app


def _ensure_email_alert_tables(app) -> None:
    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=[
                db.metadata.tables["email_alert_events"],
                db.metadata.tables["email_alert_event_deliveries"],
            ],
        )


def _make_event(
    *,
    alert_type: str,
    occurred_at: datetime,
    bucket_date: date,
    dedupe_key: str,
    payload_json: dict[str, object],
    digest_sent_at: datetime | None = None,
) -> EmailAlertEvent:
    event = EmailAlertEvent()
    event.alert_type = alert_type
    event.occurred_at = occurred_at
    event.bucket_date = bucket_date
    event.dedupe_key = dedupe_key
    event.payload_json = payload_json
    event.digest_sent_at = digest_sent_at
    return event


@pytest.mark.unit
def test_email_alerts_repository_email_channel_excludes_legacy_sent_and_historical_events(app) -> None:
    _ensure_email_alert_tables(app)

    with app.app_context():
        db.session.add_all(
            [
                _make_event(
                    alert_type="backup_status_issue",
                    occurred_at=datetime(2026, 3, 16, 1, 0, tzinfo=UTC),
                    bucket_date=date(2026, 3, 16),
                    dedupe_key="old",
                    payload_json={"instance_name": "old-db"},
                ),
                _make_event(
                    alert_type="backup_status_issue",
                    occurred_at=datetime(2026, 3, 17, 1, 0, tzinfo=UTC),
                    bucket_date=date(2026, 3, 17),
                    dedupe_key="legacy-sent",
                    payload_json={"instance_name": "legacy-sent-db"},
                    digest_sent_at=datetime(2026, 3, 17, 8, 0, tzinfo=UTC),
                ),
                _make_event(
                    alert_type="backup_status_issue",
                    occurred_at=datetime(2026, 3, 17, 2, 0, tzinfo=UTC),
                    bucket_date=date(2026, 3, 17),
                    dedupe_key="today",
                    payload_json={"instance_name": "today-db"},
                ),
            ],
        )
        db.session.commit()

        events = EmailAlertsRepository.list_pending_digest_events(
            channel="email",
            bucket_date=date(2026, 3, 17),
        )

        assert [event.dedupe_key for event in events] == ["today"]
