"""JumpServer 数据源绑定模型."""

from __future__ import annotations

from app import db
from app.utils.time_utils import time_utils


class JumpServerSourceBinding(db.Model):
    """全局唯一的 JumpServer 数据源绑定."""

    __tablename__ = "jumpserver_source_bindings"

    id = db.Column(db.Integer, primary_key=True)
    credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=False, unique=True)
    base_url = db.Column(db.String(512), nullable=False)
    org_id = db.Column(db.String(64), nullable=True)
    verify_ssl = db.Column(db.Boolean, nullable=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_sync_status = db.Column(db.String(32), nullable=True)
    last_sync_run_id = db.Column(db.String(64), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    credential = db.relationship("Credential")

    def to_dict(self) -> dict[str, object]:
        """序列化绑定状态."""
        return {
            "credential_id": self.credential_id,
            "base_url": self.base_url,
            "org_id": self.org_id,
            "verify_ssl": bool(self.verify_ssl) if self.verify_ssl is not None else None,
            "is_enabled": bool(self.is_enabled),
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_run_id": self.last_sync_run_id,
            "last_error": self.last_error,
        }
