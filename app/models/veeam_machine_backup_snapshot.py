"""Veeam 机器备份快照模型."""

from __future__ import annotations

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils


class VeeamMachineBackupSnapshot(db.Model):
    """保存最近一次成功同步的 Veeam 机器级备份快照."""

    __tablename__ = "veeam_machine_backup_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    machine_name = db.Column(db.String(255), nullable=False)
    normalized_machine_name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    latest_backup_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    backup_id = db.Column(db.String(255), nullable=True)
    backup_file_id = db.Column(db.String(255), nullable=True)
    job_name = db.Column(db.String(255), nullable=True)
    restore_point_name = db.Column(db.String(255), nullable=True)
    source_record_id = db.Column(db.String(255), nullable=True)
    restore_point_size_bytes = db.Column(db.BigInteger, nullable=True)
    backup_chain_size_bytes = db.Column(db.BigInteger, nullable=True)
    restore_point_count = db.Column(db.Integer, nullable=True)
    raw_payload = db.Column(
        db.JSON().with_variant(postgresql.JSONB(), "postgresql"),
        nullable=False,
        default=dict,
    )
    sync_run_id = db.Column(db.String(64), nullable=True)
    synced_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    def to_dict(self) -> dict[str, object]:
        """序列化快照."""
        return {
            "machine_name": self.machine_name,
            "normalized_machine_name": self.normalized_machine_name,
            "latest_backup_at": self.latest_backup_at.isoformat() if self.latest_backup_at else None,
            "backup_id": self.backup_id,
            "backup_file_id": self.backup_file_id,
            "job_name": self.job_name,
            "restore_point_name": self.restore_point_name,
            "source_record_id": self.source_record_id,
            "restore_point_size_bytes": self.restore_point_size_bytes,
            "backup_chain_size_bytes": self.backup_chain_size_bytes,
            "restore_point_count": self.restore_point_count,
            "sync_run_id": self.sync_run_id,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
