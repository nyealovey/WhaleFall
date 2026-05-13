"""告警事件投递状态模型."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils


class EmailAlertEventDelivery(db.Model):
    """告警事件按通道记录投递状态."""

    __tablename__ = "email_alert_event_deliveries"

    __table_args__ = (
        db.UniqueConstraint("event_id", "channel", name="uq_email_alert_event_deliveries_event_channel"),
        db.Index("ix_email_alert_event_deliveries_channel_status", "channel", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("email_alert_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="pending")
    delivered_at = db.Column(db.DateTime(timezone=True), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    details_json = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)
