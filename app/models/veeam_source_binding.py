"""Veeam 数据源绑定模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import VeeamSourceBindingOrmFields


class VeeamSourceBinding(db.Model):
    """全局唯一的 Veeam 数据源绑定."""

    __tablename__ = "veeam_source_bindings"

    id = db.Column(db.Integer, primary_key=True)
    credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=False, unique=True)
    server_host = db.Column(db.String(255), nullable=False)
    server_port = db.Column(db.Integer, nullable=False)
    api_version = db.Column(db.String(32), nullable=False)
    verify_ssl = db.Column(db.Boolean, nullable=True)
    match_domains = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=False,
        default=list,
    )
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_sync_status = db.Column(db.String(32), nullable=True)
    last_sync_run_id = db.Column(db.String(64), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    credential = db.relationship("Credential")

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[VeeamSourceBindingOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def to_dict(self) -> dict[str, object]:
        """序列化绑定状态."""
        domains = self.match_domains if isinstance(self.match_domains, list) else []
        return {
            "credential_id": self.credential_id,
            "server_host": self.server_host,
            "server_port": self.server_port,
            "api_version": self.api_version,
            "verify_ssl": bool(self.verify_ssl) if self.verify_ssl is not None else None,
            "match_domains": [str(item).strip() for item in domains if str(item).strip()],
            "is_enabled": bool(self.is_enabled),
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_run_id": self.last_sync_run_id,
            "last_error": self.last_error,
        }
