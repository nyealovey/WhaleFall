"""SQL Server AG 数据库同步状态模型."""

from __future__ import annotations

from app import db
from app.utils.time_utils import time_utils


class SQLServerAgDatabaseSyncState(db.Model):
    """SQL Server AG database/replica 最近一次同步健康状态."""

    __tablename__ = "sqlserver_ag_database_sync_states"

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey("sqlserver_clusters.id"), nullable=False, index=True)
    availability_group_id = db.Column(db.Integer, db.ForeignKey("sqlserver_availability_groups.id"), nullable=True, index=True)
    ag_name = db.Column(db.String(128), nullable=False)
    database_name = db.Column(db.String(255), nullable=False)
    replica_server_name = db.Column(db.String(255), nullable=False)
    synchronization_state_desc = db.Column(db.String(64), nullable=True)
    synchronization_health_desc = db.Column(db.String(64), nullable=True)
    database_state_desc = db.Column(db.String(64), nullable=True)
    is_suspended = db.Column(db.Boolean, nullable=False, default=False)
    suspend_reason_desc = db.Column(db.String(128), nullable=True)
    log_send_queue_size = db.Column(db.Integer, nullable=True)
    redo_queue_size = db.Column(db.Integer, nullable=True)
    is_abnormal = db.Column(db.Boolean, nullable=False, default=False, index=True)
    error_summary = db.Column(db.Text, nullable=True)
    last_checked_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    cluster = db.relationship("SQLServerCluster")
    availability_group = db.relationship("SQLServerAvailabilityGroup")

    __table_args__ = (
        db.UniqueConstraint(
            "cluster_id",
            "ag_name",
            "database_name",
            "replica_server_name",
            name="uq_sqlserver_ag_db_sync_state_scope",
        ),
        db.Index("ix_sqlserver_ag_db_sync_state_cluster_abnormal", "cluster_id", "is_abnormal"),
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "availability_group_id": self.availability_group_id,
            "ag_name": self.ag_name,
            "database_name": self.database_name,
            "replica_server_name": self.replica_server_name,
            "synchronization_state_desc": self.synchronization_state_desc,
            "synchronization_health_desc": self.synchronization_health_desc,
            "database_state_desc": self.database_state_desc,
            "is_suspended": bool(self.is_suspended),
            "suspend_reason_desc": self.suspend_reason_desc,
            "log_send_queue_size": self.log_send_queue_size,
            "redo_queue_size": self.redo_queue_size,
            "is_abnormal": bool(self.is_abnormal),
            "error_summary": self.error_summary,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
        }
