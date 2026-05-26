"""Add MySQL replication diagnostic fields.

Revision ID: 20260526130000
Revises: 20260526090000
Create Date: 2026-05-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260526130000"
down_revision = "20260526090000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column("mysql_cluster_instances", sa.Column("io_state", sa.String(length=255), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("source_log_file", sa.String(length=255), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("read_source_log_pos", sa.Integer(), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("relay_source_log_file", sa.String(length=255), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("exec_source_log_pos", sa.Integer(), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("sql_delay", sa.Integer(), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("retrieved_gtid_set", sa.Text(), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("executed_gtid_set", sa.Text(), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("last_io_error", sa.Text(), nullable=True))
    op.add_column("mysql_cluster_instances", sa.Column("last_sql_error", sa.Text(), nullable=True))


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("mysql_cluster_instances", "last_sql_error")
    op.drop_column("mysql_cluster_instances", "last_io_error")
    op.drop_column("mysql_cluster_instances", "executed_gtid_set")
    op.drop_column("mysql_cluster_instances", "retrieved_gtid_set")
    op.drop_column("mysql_cluster_instances", "sql_delay")
    op.drop_column("mysql_cluster_instances", "exec_source_log_pos")
    op.drop_column("mysql_cluster_instances", "relay_source_log_file")
    op.drop_column("mysql_cluster_instances", "read_source_log_pos")
    op.drop_column("mysql_cluster_instances", "source_log_file")
    op.drop_column("mysql_cluster_instances", "io_state")
