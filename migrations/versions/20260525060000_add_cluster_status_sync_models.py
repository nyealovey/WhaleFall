"""add cluster status sync models.

Revision ID: 20260525060000
Revises: 20260521160000
Create Date: 2026-05-25 06:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260525060000"
down_revision = "20260521160000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mysql_clusters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("topology_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("last_topology_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_topology_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_mysql_clusters_name", "mysql_clusters", ["name"])

    op.create_table(
        "mysql_cluster_instances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("replication_role", sa.String(length=32), nullable=False),
        sa.Column("replication_status", sa.String(length=32), nullable=False),
        sa.Column("source_host", sa.String(length=255), nullable=True),
        sa.Column("source_port", sa.Integer(), nullable=True),
        sa.Column("io_running", sa.String(length=16), nullable=True),
        sa.Column("sql_running", sa.String(length=16), nullable=True),
        sa.Column("seconds_behind_source", sa.Integer(), nullable=True),
        sa.Column("read_only", sa.Boolean(), nullable=True),
        sa.Column("super_read_only", sa.Boolean(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cluster_id"], ["mysql_clusters.id"]),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cluster_id", "instance_id", name="uq_mysql_cluster_instance"),
        sa.UniqueConstraint("instance_id", name="uq_mysql_cluster_instance_instance_id"),
    )
    op.create_index("ix_mysql_cluster_instances_cluster_id", "mysql_cluster_instances", ["cluster_id"])
    op.create_index("ix_mysql_cluster_instances_instance_id", "mysql_cluster_instances", ["instance_id"])

    op.create_table(
        "sqlserver_ag_database_sync_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("availability_group_id", sa.Integer(), nullable=True),
        sa.Column("ag_name", sa.String(length=128), nullable=False),
        sa.Column("database_name", sa.String(length=255), nullable=False),
        sa.Column("replica_server_name", sa.String(length=255), nullable=False),
        sa.Column("synchronization_state_desc", sa.String(length=64), nullable=True),
        sa.Column("synchronization_health_desc", sa.String(length=64), nullable=True),
        sa.Column("database_state_desc", sa.String(length=64), nullable=True),
        sa.Column("is_suspended", sa.Boolean(), nullable=False),
        sa.Column("suspend_reason_desc", sa.String(length=128), nullable=True),
        sa.Column("log_send_queue_size", sa.Integer(), nullable=True),
        sa.Column("redo_queue_size", sa.Integer(), nullable=True),
        sa.Column("is_abnormal", sa.Boolean(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["availability_group_id"], ["sqlserver_availability_groups.id"]),
        sa.ForeignKeyConstraint(["cluster_id"], ["sqlserver_clusters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cluster_id",
            "ag_name",
            "database_name",
            "replica_server_name",
            name="uq_sqlserver_ag_db_sync_state_scope",
        ),
    )
    op.create_index(
        "ix_sqlserver_ag_db_sync_state_cluster_abnormal",
        "sqlserver_ag_database_sync_states",
        ["cluster_id", "is_abnormal"],
    )
    op.create_index("ix_sqlserver_ag_database_sync_states_availability_group_id", "sqlserver_ag_database_sync_states", ["availability_group_id"])
    op.create_index("ix_sqlserver_ag_database_sync_states_cluster_id", "sqlserver_ag_database_sync_states", ["cluster_id"])
    op.create_index("ix_sqlserver_ag_database_sync_states_is_abnormal", "sqlserver_ag_database_sync_states", ["is_abnormal"])
    op.create_index("ix_sqlserver_ag_database_sync_states_last_checked_at", "sqlserver_ag_database_sync_states", ["last_checked_at"])


def downgrade() -> None:
    op.drop_index("ix_sqlserver_ag_database_sync_states_last_checked_at", table_name="sqlserver_ag_database_sync_states")
    op.drop_index("ix_sqlserver_ag_database_sync_states_is_abnormal", table_name="sqlserver_ag_database_sync_states")
    op.drop_index("ix_sqlserver_ag_database_sync_states_cluster_id", table_name="sqlserver_ag_database_sync_states")
    op.drop_index(
        "ix_sqlserver_ag_database_sync_states_availability_group_id",
        table_name="sqlserver_ag_database_sync_states",
    )
    op.drop_index("ix_sqlserver_ag_db_sync_state_cluster_abnormal", table_name="sqlserver_ag_database_sync_states")
    op.drop_table("sqlserver_ag_database_sync_states")
    op.drop_index("ix_mysql_cluster_instances_instance_id", table_name="mysql_cluster_instances")
    op.drop_index("ix_mysql_cluster_instances_cluster_id", table_name="mysql_cluster_instances")
    op.drop_table("mysql_cluster_instances")
    op.drop_index("ix_mysql_clusters_name", table_name="mysql_clusters")
    op.drop_table("mysql_clusters")
