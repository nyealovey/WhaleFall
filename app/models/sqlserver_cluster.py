"""SQL Server 群集与 AG 模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import (
        SQLServerAvailabilityGroupOrmFields,
        SQLServerClusterInstanceOrmFields,
        SQLServerClusterOrmFields,
    )


class SQLServerCluster(db.Model):
    """SQL Server 群集."""

    __tablename__ = "sqlserver_clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    instances = db.relationship(
        "SQLServerClusterInstance",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )
    availability_groups = db.relationship(
        "SQLServerAvailabilityGroup",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[SQLServerClusterOrmFields]) -> None:
            ...

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "is_enabled": bool(self.is_enabled),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SQLServerClusterInstance(db.Model):
    """SQL Server 群集与实例绑定."""

    __tablename__ = "sqlserver_cluster_instances"

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey("sqlserver_clusters.id"), nullable=False, index=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)

    cluster = db.relationship("SQLServerCluster", back_populates="instances")
    instance = db.relationship("Instance")

    __table_args__ = (
        db.UniqueConstraint("cluster_id", "instance_id", name="uq_sqlserver_cluster_instance"),
        db.UniqueConstraint("instance_id", name="uq_sqlserver_cluster_instance_instance_id"),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[SQLServerClusterInstanceOrmFields]) -> None:
            ...


class SQLServerAvailabilityGroup(db.Model):
    """SQL Server 可用性组配置."""

    __tablename__ = "sqlserver_availability_groups"

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey("sqlserver_clusters.id"), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    listener_name = db.Column(db.String(255), nullable=True)
    listener_host = db.Column(db.String(255), nullable=False)
    listener_port = db.Column(db.Integer, nullable=False, default=1433)
    credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=True)
    account_credential_id = db.Column(db.Integer, db.ForeignKey("credentials.id"), nullable=True)
    connection_database = db.Column(db.String(255), nullable=True)
    contained_enabled = db.Column(db.Boolean, nullable=False, default=False)
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_sync_status = db.Column(db.String(32), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    cluster = db.relationship("SQLServerCluster", back_populates="availability_groups")
    credential = db.relationship("Credential", foreign_keys=[credential_id])
    account_credential = db.relationship("Credential", foreign_keys=[account_credential_id])

    __table_args__ = (
        db.UniqueConstraint("cluster_id", "name", name="uq_sqlserver_ag_cluster_name"),
        db.Index("ix_sqlserver_ag_cluster_contained", "cluster_id", "contained_enabled", "is_enabled"),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[SQLServerAvailabilityGroupOrmFields]) -> None:
            ...

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "name": self.name,
            "listener_name": self.listener_name,
            "listener_host": self.listener_host,
            "listener_port": self.listener_port,
            "credential_id": self.credential_id,
            "account_credential_id": self.account_credential_id,
            "connection_database": self.connection_database,
            "contained_enabled": bool(self.contained_enabled),
            "is_enabled": bool(self.is_enabled),
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_sync_status": self.last_sync_status,
            "last_error": self.last_error,
        }
