"""MySQL 群集与实例拓扑状态模型."""

from __future__ import annotations

from app import db
from app.utils.time_utils import time_utils


class MySQLCluster(db.Model):
    """MySQL 群集."""

    __tablename__ = "mysql_clusters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True, index=True)
    topology_type = db.Column(db.String(32), nullable=False, default="replication")
    description = db.Column(db.Text, nullable=False, default="")
    is_enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_topology_sync_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_topology_sync_status = db.Column(db.String(32), nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    instances = db.relationship(
        "MySQLClusterInstance",
        back_populates="cluster",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "topology_type": self.topology_type,
            "description": self.description,
            "is_enabled": bool(self.is_enabled),
            "last_topology_sync_at": self.last_topology_sync_at.isoformat() if self.last_topology_sync_at else None,
            "last_topology_sync_status": self.last_topology_sync_status,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MySQLClusterInstance(db.Model):
    """MySQL 群集与实例绑定，以及最近一次主从拓扑检测结果."""

    __tablename__ = "mysql_cluster_instances"

    id = db.Column(db.Integer, primary_key=True)
    cluster_id = db.Column(db.Integer, db.ForeignKey("mysql_clusters.id"), nullable=False, index=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("instances.id"), nullable=False, index=True)
    replication_role = db.Column(db.String(32), nullable=False, default="unknown")
    replication_status = db.Column(db.String(32), nullable=False, default="unknown")
    source_host = db.Column(db.String(255), nullable=True)
    source_port = db.Column(db.Integer, nullable=True)
    io_running = db.Column(db.String(16), nullable=True)
    sql_running = db.Column(db.String(16), nullable=True)
    seconds_behind_source = db.Column(db.Integer, nullable=True)
    io_state = db.Column(db.String(255), nullable=True)
    source_log_file = db.Column(db.String(255), nullable=True)
    read_source_log_pos = db.Column(db.Integer, nullable=True)
    relay_source_log_file = db.Column(db.String(255), nullable=True)
    exec_source_log_pos = db.Column(db.Integer, nullable=True)
    sql_delay = db.Column(db.Integer, nullable=True)
    retrieved_gtid_set = db.Column(db.Text, nullable=True)
    executed_gtid_set = db.Column(db.Text, nullable=True)
    read_only = db.Column(db.Boolean, nullable=True)
    super_read_only = db.Column(db.Boolean, nullable=True)
    last_io_error = db.Column(db.Text, nullable=True)
    last_sql_error = db.Column(db.Text, nullable=True)
    last_error = db.Column(db.Text, nullable=True)
    last_checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=time_utils.now, onupdate=time_utils.now)

    cluster = db.relationship("MySQLCluster", back_populates="instances")
    instance = db.relationship("Instance")

    __table_args__ = (
        db.UniqueConstraint("cluster_id", "instance_id", name="uq_mysql_cluster_instance"),
        db.UniqueConstraint("instance_id", name="uq_mysql_cluster_instance_instance_id"),
    )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "cluster_id": self.cluster_id,
            "instance_id": self.instance_id,
            "replication_role": self.replication_role,
            "replication_status": self.replication_status,
            "source_host": self.source_host,
            "source_port": self.source_port,
            "io_running": self.io_running,
            "sql_running": self.sql_running,
            "seconds_behind_source": self.seconds_behind_source,
            "io_state": self.io_state,
            "source_log_file": self.source_log_file,
            "read_source_log_pos": self.read_source_log_pos,
            "relay_source_log_file": self.relay_source_log_file,
            "exec_source_log_pos": self.exec_source_log_pos,
            "sql_delay": self.sql_delay,
            "retrieved_gtid_set": self.retrieved_gtid_set,
            "executed_gtid_set": self.executed_gtid_set,
            "read_only": self.read_only,
            "super_read_only": self.super_read_only,
            "last_io_error": self.last_io_error,
            "last_sql_error": self.last_sql_error,
            "last_error": self.last_error,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
        }
