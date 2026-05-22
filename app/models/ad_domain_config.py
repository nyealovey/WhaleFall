"""AD 域同步配置模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import AdDomainConfigOrmFields


class AdDomainConfig(db.Model):
    """AD 域同步配置."""

    __tablename__ = "ad_domain_configs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    netbios_name = db.Column(db.String(64), nullable=False, index=True)
    domain_controllers = db.Column(db.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False, default=list)
    ldap_port = db.Column(db.Integer, nullable=False, default=636)
    use_ssl = db.Column(db.Boolean, nullable=False, default=True)
    verify_ssl = db.Column(db.Boolean, nullable=True)
    base_dn = db.Column(db.String(512), nullable=False)
    credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    description = db.Column(db.Text, nullable=True)
    last_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_sync_status = db.Column(db.String(32), nullable=True)
    last_sync_run_id = db.Column(db.String(64), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    credential = db.relationship("Credential")

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[AdDomainConfigOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def to_dict(self) -> dict[str, object]:
        """序列化域配置状态."""
        controllers = self.domain_controllers if isinstance(self.domain_controllers, list) else []
        return {
            "id": self.id,
            "name": self.name,
            "netbios_name": self.netbios_name,
            "domain_controllers": [str(item).strip() for item in controllers if str(item).strip()],
            "ldap_port": self.ldap_port,
            "use_ssl": bool(self.use_ssl),
            "verify_ssl": bool(self.verify_ssl) if self.verify_ssl is not None else None,
            "base_dn": self.base_dn,
            "credential_id": self.credential_id,
            "is_enabled": bool(self.is_enabled),
            "description": self.description,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "last_sync_run_id": self.last_sync_run_id,
            "last_error": self.last_error,
        }
