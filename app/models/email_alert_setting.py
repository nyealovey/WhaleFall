"""邮件告警配置模型."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.password_crypto_utils import get_password_manager
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
    backup_issue_enabled = db.Column(db.Boolean, nullable=False, default=False)
    feishu_enabled = db.Column(db.Boolean, nullable=False, default=False)
    feishu_webhook_url_encrypted = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    def set_feishu_webhook_url(self, webhook_url: str) -> None:
        """加密保存飞书机器人 URL."""
        normalized_url = webhook_url.strip()
        self.feishu_webhook_url_encrypted = (
            get_password_manager().encrypt_password(normalized_url) if normalized_url else None
        )

    def get_feishu_webhook_url(self) -> str:
        """解密飞书机器人 URL."""
        encrypted_url = str(self.feishu_webhook_url_encrypted or "")
        if not encrypted_url:
            return ""
        if get_password_manager().is_encrypted(encrypted_url):
            return get_password_manager().decrypt_password(encrypted_url)
        return ""

    def get_feishu_webhook_url_masked(self) -> str | None:
        """返回飞书机器人 URL 掩码."""
        webhook_url = self.get_feishu_webhook_url()
        if not webhook_url:
            return None
        visible_tail = 4
        mask_length = 10
        if len(webhook_url) <= visible_tail:
            return "*" * len(webhook_url)
        prefix, separator, token = webhook_url.rpartition("/")
        if separator and len(token) > visible_tail:
            return f"{prefix}{separator}{'*' * mask_length}{token[-visible_tail:]}"
        return f"{'*' * mask_length}{webhook_url[-visible_tail:]}"

    def to_dict(self) -> dict[str, object]:
        """序列化邮件告警配置."""
        feishu_webhook_url_masked = self.get_feishu_webhook_url_masked()
        return {
            "global_enabled": bool(self.global_enabled),
            "recipients": list(self.recipients_json or []),
            "database_capacity_enabled": bool(self.database_capacity_enabled),
            "database_capacity_percent_threshold": int(self.database_capacity_percent_threshold or 0),
            "database_capacity_absolute_gb_threshold": int(self.database_capacity_absolute_gb_threshold or 0),
            "account_sync_failure_enabled": bool(self.account_sync_failure_enabled),
            "database_sync_failure_enabled": bool(self.database_sync_failure_enabled),
            "privileged_account_enabled": bool(self.privileged_account_enabled),
            "backup_issue_enabled": bool(self.backup_issue_enabled),
            "feishu_enabled": bool(self.feishu_enabled),
            "feishu_webhook_url_configured": feishu_webhook_url_masked is not None,
            "feishu_webhook_url_masked": feishu_webhook_url_masked,
        }
