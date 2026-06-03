"""add sqlserver ag replica sync states.

Revision ID: 20260525100000
Revises: 20260525080000
Create Date: 2026-05-25 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260525100000"
down_revision = "20260525080000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sqlserver_ag_replica_sync_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("availability_group_id", sa.Integer(), nullable=True),
        sa.Column("ag_name", sa.String(length=128), nullable=False),
        sa.Column("replica_server_name", sa.String(length=255), nullable=False),
        sa.Column("role_desc", sa.String(length=64), nullable=True),
        sa.Column("availability_mode_desc", sa.String(length=64), nullable=True),
        sa.Column("failover_mode_desc", sa.String(length=64), nullable=True),
        sa.Column("seeding_mode_desc", sa.String(length=64), nullable=True),
        sa.Column("synchronization_health_desc", sa.String(length=64), nullable=True),
        sa.Column("connected_state_desc", sa.String(length=64), nullable=True),
        sa.Column("operational_state_desc", sa.String(length=64), nullable=True),
        sa.Column("recovery_health_desc", sa.String(length=64), nullable=True),
        sa.Column("cluster_state_desc", sa.String(length=64), nullable=True),
        sa.Column("cluster_type_desc", sa.String(length=64), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
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
            "replica_server_name",
            name="uq_sqlserver_ag_replica_sync_state_scope",
        ),
    )
    op.create_index(
        "ix_sqlserver_ag_replica_sync_state_cluster_abnormal",
        "sqlserver_ag_replica_sync_states",
        ["cluster_id", "is_abnormal"],
    )
    op.create_index(
        "ix_sqlserver_ag_replica_sync_states_availability_group_id",
        "sqlserver_ag_replica_sync_states",
        ["availability_group_id"],
    )
    op.create_index("ix_sqlserver_ag_replica_sync_states_cluster_id", "sqlserver_ag_replica_sync_states", ["cluster_id"])
    op.create_index("ix_sqlserver_ag_replica_sync_states_is_abnormal", "sqlserver_ag_replica_sync_states", ["is_abnormal"])
    op.create_index(
        "ix_sqlserver_ag_replica_sync_states_last_checked_at",
        "sqlserver_ag_replica_sync_states",
        ["last_checked_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sqlserver_ag_replica_sync_states_last_checked_at", table_name="sqlserver_ag_replica_sync_states")
    op.drop_index("ix_sqlserver_ag_replica_sync_states_is_abnormal", table_name="sqlserver_ag_replica_sync_states")
    op.drop_index("ix_sqlserver_ag_replica_sync_states_cluster_id", table_name="sqlserver_ag_replica_sync_states")
    op.drop_index(
        "ix_sqlserver_ag_replica_sync_states_availability_group_id",
        table_name="sqlserver_ag_replica_sync_states",
    )
    op.drop_index(
        "ix_sqlserver_ag_replica_sync_state_cluster_abnormal",
        table_name="sqlserver_ag_replica_sync_states",
    )
    op.drop_table("sqlserver_ag_replica_sync_states")
