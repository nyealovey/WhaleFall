"""Add veeam backup metrics columns.

Revision ID: 20260325170000
Revises: 20260325063000
Create Date: 2026-03-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260325170000"
down_revision = "20260325063000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column("veeam_machine_backup_snapshots", sa.Column("backup_id", sa.String(length=255), nullable=True))
    op.add_column("veeam_machine_backup_snapshots", sa.Column("backup_file_id", sa.String(length=255), nullable=True))
    op.add_column(
        "veeam_machine_backup_snapshots",
        sa.Column("restore_point_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "veeam_machine_backup_snapshots",
        sa.Column("backup_chain_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column("veeam_machine_backup_snapshots", sa.Column("restore_point_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("veeam_machine_backup_snapshots", "restore_point_count")
    op.drop_column("veeam_machine_backup_snapshots", "backup_chain_size_bytes")
    op.drop_column("veeam_machine_backup_snapshots", "restore_point_size_bytes")
    op.drop_column("veeam_machine_backup_snapshots", "backup_file_id")
    op.drop_column("veeam_machine_backup_snapshots", "backup_id")
