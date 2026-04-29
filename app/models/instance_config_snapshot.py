"""实例级配置快照模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import InstanceConfigSnapshotOrmFields


class InstanceConfigSnapshot(db.Model):
    """实例级配置快照."""

    __tablename__ = "instance_config_snapshots"

    id = db.Column(Integer, primary_key=True)
    instance_id = db.Column(Integer, ForeignKey("instances.id"), nullable=False)
    db_type = db.Column(String(50), nullable=False)
    config_key = db.Column(String(64), nullable=False)
    snapshot = db.Column(db.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True)
    facts = db.Column(db.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True)
    last_sync_time = db.Column(DateTime(timezone=True), nullable=True)
    created_at = db.Column(DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(
        DateTime(timezone=True),
        nullable=False,
        default=time_utils.now,
        onupdate=time_utils.now,
    )

    instance = db.relationship("Instance", backref="config_snapshots")

    __table_args__ = (
        UniqueConstraint(
            "instance_id",
            "config_key",
            name="uq_instance_config_snapshot_instance_config_key",
        ),
        Index(
            "ix_instance_config_snapshots_instance_config_key",
            "instance_id",
            "config_key",
        ),
        Index("ix_instance_config_snapshots_config_key", "config_key"),
        Index("ix_instance_config_snapshots_last_sync_time", "last_sync_time"),
    )

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[InstanceConfigSnapshotOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...
