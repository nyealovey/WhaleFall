"""邮件告警配置与事件 Repository."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import asc, desc

from app import db
from app.models.database_size_stat import DatabaseSizeStat
from app.models.email_alert_event import EmailAlertEvent
from app.models.email_alert_event_delivery import EmailAlertEventDelivery
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
    def upsert_backup_issue_event(**payload: object) -> bool:
        alert_type = str(payload.get("alert_type") or "")
        bucket_date = payload.get("bucket_date")
        dedupe_key = str(payload.get("dedupe_key") or "")
        existing = (
            EmailAlertEvent.query.filter(
                EmailAlertEvent.alert_type == alert_type,
                EmailAlertEvent.bucket_date == bucket_date,
                EmailAlertEvent.dedupe_key == dedupe_key,
            )
            .order_by(EmailAlertEvent.id.asc())
            .first()
        )
        if existing is None:
            EmailAlertsRepository.create_event(**payload)
            return True
        if existing.digest_sent_at is not None:
            return False
        for field_name, value in payload.items():
            if hasattr(existing, str(field_name)):
                setattr(existing, str(field_name), value)
        db.session.flush()
        return False

    @staticmethod
    def delete_pending_backup_issue_events_not_in(*, bucket_date: date, dedupe_keys: set[str]) -> int:
        sent_delivery_exists = (
            db.session.query(EmailAlertEventDelivery.id)
            .filter(
                EmailAlertEventDelivery.event_id == EmailAlertEvent.id,
                EmailAlertEventDelivery.status == "sent",
            )
            .exists()
        )
        query = EmailAlertEvent.query.filter(
            EmailAlertEvent.alert_type == "backup_status_issue",
            EmailAlertEvent.bucket_date == bucket_date,
            EmailAlertEvent.digest_sent_at.is_(None),
            ~sent_delivery_exists,
        )
        if dedupe_keys:
            query = query.filter(EmailAlertEvent.dedupe_key.notin_(sorted(dedupe_keys)))
        deleted = query.delete(synchronize_session=False)
        db.session.flush()
        return int(deleted or 0)

    @staticmethod
    def list_pending_digest_events(channel: str | None = None) -> list[EmailAlertEvent]:
        query = EmailAlertEvent.query
        if channel:
            sent_exists = (
                db.session.query(EmailAlertEventDelivery.id)
                .filter(
                    EmailAlertEventDelivery.event_id == EmailAlertEvent.id,
                    EmailAlertEventDelivery.channel == channel,
                    EmailAlertEventDelivery.status == "sent",
                )
                .exists()
            )
            query = query.filter(~sent_exists)
        else:
            query = query.filter(EmailAlertEvent.digest_sent_at.is_(None))
        return query.order_by(asc(EmailAlertEvent.occurred_at), asc(EmailAlertEvent.id)).all()

    @staticmethod
    def get_bucket_event_counts(bucket_date: date, channels: list[str] | None = None) -> dict[str, dict[str, int]]:
        stats: dict[str, dict[str, int]] = {}
        events = EmailAlertEvent.query.filter(EmailAlertEvent.bucket_date == bucket_date).all()
        if channels:
            event_ids = [int(event.id) for event in events]
            deliveries = (
                EmailAlertEventDelivery.query.filter(
                    EmailAlertEventDelivery.event_id.in_(event_ids),
                    EmailAlertEventDelivery.channel.in_(channels),
                    EmailAlertEventDelivery.status == "sent",
                ).all()
                if event_ids
                else []
            )
            sent_channels_by_event: dict[int, set[str]] = {}
            for delivery in deliveries:
                sent_channels_by_event.setdefault(int(delivery.event_id), set()).add(str(delivery.channel))
            required_channels = set(channels)
            for event in events:
                alert_type = str(event.alert_type)
                bucket = stats.setdefault(alert_type, {"pending_count": 0, "sent_count": 0})
                sent_channels = sent_channels_by_event.get(int(event.id), set())
                if required_channels and required_channels <= sent_channels:
                    bucket["sent_count"] += 1
                else:
                    bucket["pending_count"] += 1
            return stats

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
    def record_digest_delivery(
        *,
        channel: str,
        event_ids: list[int],
        delivered_at,
        status: str,
        error_message: str | None = None,
    ) -> None:
        if not event_ids:
            return
        existing_rows = EmailAlertEventDelivery.query.filter(
            EmailAlertEventDelivery.event_id.in_(event_ids),
            EmailAlertEventDelivery.channel == channel,
        ).all()
        existing_by_event_id = {int(row.event_id): row for row in existing_rows}
        for event_id in event_ids:
            delivery = existing_by_event_id.get(int(event_id))
            if delivery is None:
                delivery = EmailAlertEventDelivery()
                delivery.event_id = int(event_id)
                delivery.channel = channel
                db.session.add(delivery)
            delivery.status = status
            delivery.delivered_at = delivered_at if status == "sent" else None
            delivery.error_message = error_message
            delivery.details_json = {}
        if channel == "email" and status == "sent":
            EmailAlertsRepository.mark_events_digest_sent(event_ids, delivered_at)
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
