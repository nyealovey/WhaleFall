"""邮件告警配置模型."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils


class EmailAlertSetting(db.Model):
    """邮件告警业务配置."""

    __tablename__ = "email_alert_settings"

    id = db.Column(db.Integer, primary_key=True)
    global_enabled = db.Column(db.Boolean, nullable=False, default=False)
    recipients_json = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )
    database_capacity_enabled = db.Column(db.Boolean, nullable=False, default=False)
    database_capacity_percent_threshold = db.Column(db.Integer, nullable=False, default=30)
    database_capacity_absolute_gb_threshold = db.Column(db.Integer, nullable=False, default=20)
    account_sync_failure_enabled = db.Column(db.Boolean, nullable=False, default=False)
    database_sync_failure_enabled = db.Column(db.Boolean, nullable=False, default=False)
    privileged_account_enabled = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    def to_dict(self) -> dict[str, object]:
        """序列化邮件告警配置."""
        return {
            "global_enabled": bool(self.global_enabled),
            "recipients": list(self.recipients_json or []),
            "database_capacity_enabled": bool(self.database_capacity_enabled),
            "database_capacity_percent_threshold": int(self.database_capacity_percent_threshold or 0),
            "database_capacity_absolute_gb_threshold": int(self.database_capacity_absolute_gb_threshold or 0),
            "account_sync_failure_enabled": bool(self.account_sync_failure_enabled),
            "database_sync_failure_enabled": bool(self.database_sync_failure_enabled),
            "privileged_account_enabled": bool(self.privileged_account_enabled),
        }
