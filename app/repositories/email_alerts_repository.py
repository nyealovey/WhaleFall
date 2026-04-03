"""邮件告警配置与事件 Repository."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import asc, desc

from app import db
from app.models.database_size_stat import DatabaseSizeStat
from app.models.email_alert_event import EmailAlertEvent
from app.models.email_alert_setting import EmailAlertSetting


class EmailAlertsRepository:
    """邮件告警配置与事件仓储."""

    @staticmethod
    def get_settings() -> EmailAlertSetting | None:
        return EmailAlertSetting.query.order_by(EmailAlertSetting.id.asc()).first()

    @staticmethod
    def add_settings(settings: EmailAlertSetting) -> None:
        db.session.add(settings)
        db.session.flush()

    @staticmethod
    def create_event(**payload: object) -> None:
        event = EmailAlertEvent(**payload)
        with db.session.begin_nested():
            db.session.add(event)
            db.session.flush()

    @staticmethod
    def list_pending_digest_events() -> list[EmailAlertEvent]:
        return (
            EmailAlertEvent.query.filter(EmailAlertEvent.digest_sent_at.is_(None))
            .order_by(asc(EmailAlertEvent.occurred_at), asc(EmailAlertEvent.id))
            .all()
        )

    @staticmethod
    def get_bucket_event_counts(bucket_date: date) -> dict[str, dict[str, int]]:
        stats: dict[str, dict[str, int]] = {}
        events = EmailAlertEvent.query.filter(EmailAlertEvent.bucket_date == bucket_date).all()
        for event in events:
            alert_type = str(event.alert_type)
            bucket = stats.setdefault(alert_type, {"pending_count": 0, "sent_count": 0})
            if event.digest_sent_at is None:
                bucket["pending_count"] += 1
            else:
                bucket["sent_count"] += 1
        return stats

    @staticmethod
    def mark_events_digest_sent(event_ids: list[int], sent_at) -> None:
        if not event_ids:
            return
        (
            EmailAlertEvent.query.filter(EmailAlertEvent.id.in_(event_ids)).update(
                {"digest_sent_at": sent_at}, synchronize_session=False
            )
        )
        db.session.flush()

    @staticmethod
    def find_recent_database_baseline(
        *,
        instance_id: int,
        database_name: str,
        current_collected_date: date,
        lookback_days: int,
    ) -> DatabaseSizeStat | None:
        lower_bound = current_collected_date - timedelta(days=lookback_days)
        return (
            DatabaseSizeStat.query.filter(
                DatabaseSizeStat.instance_id == instance_id,
                DatabaseSizeStat.database_name == database_name,
                DatabaseSizeStat.collected_date < current_collected_date,
                DatabaseSizeStat.collected_date >= lower_bound,
            )
            .order_by(
                desc(DatabaseSizeStat.collected_date),
                desc(DatabaseSizeStat.collected_at),
                desc(DatabaseSizeStat.id),
            )
            .first()
        )
