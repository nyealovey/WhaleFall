"""邮件告警事件模型."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils


class EmailAlertEvent(db.Model):
    """待汇总发送的邮件告警事件."""

    __tablename__ = "email_alert_events"

    __table_args__ = (
        db.UniqueConstraint("alert_type", "bucket_date", "dedupe_key", name="uq_email_alert_events_dedupe"),
        db.Index("ix_email_alert_events_bucket_date", "bucket_date"),
        db.Index("ix_email_alert_events_digest_sent_at", "digest_sent_at"),
    )

    id = db.Column(db.Integer, primary_key=True)
    alert_type = db.Column(db.String(64), nullable=False, index=True)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    bucket_date = db.Column(db.Date, nullable=False)
    dedupe_key = db.Column(db.String(255), nullable=False)
    instance_id = db.Column(db.Integer, nullable=True, index=True)
    database_name = db.Column(db.String(255), nullable=True)
    username = db.Column(db.String(255), nullable=True)
    run_id = db.Column(db.String(36), nullable=True, index=True)
    session_id = db.Column(db.String(36), nullable=True, index=True)
    payload_json = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )
    digest_sent_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)
