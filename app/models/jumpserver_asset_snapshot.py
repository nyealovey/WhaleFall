"""JumpServer 数据库资产快照模型."""

from __future__ import annotations

from typing import TYPE_CHECKING, Unpack

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from app.core.types.orm_kwargs import JumpServerAssetSnapshotOrmFields


class JumpServerAssetSnapshot(db.Model):
    """保存最近一次成功同步的 JumpServer 数据库资产快照."""

    __tablename__ = "jumpserver_asset_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    db_type = db.Column(db.String(50), nullable=False, index=True)
    host = db.Column(db.String(255), nullable=False, index=True)
    port = db.Column(db.Integer, nullable=False, index=True)
    raw_payload = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )
    sync_run_id = db.Column(db.String(64), nullable=True)
    synced_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    if TYPE_CHECKING:

        def __init__(self, **orm_fields: Unpack[JumpServerAssetSnapshotOrmFields]) -> None:
            """Type-checking helper for ORM keyword arguments."""
            ...

    def to_dict(self) -> dict[str, object]:
        """序列化快照."""
        return {
            "external_id": self.external_id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "sync_run_id": self.sync_run_id,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
