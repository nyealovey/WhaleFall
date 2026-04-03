"""Add veeam machine ip columns.

Revision ID: 20260403060000
Revises: 20260325170000
Create Date: 2026-04-03

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260403060000"
down_revision = "20260325170000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add machine_ip and normalized_machine_ip columns."""
    op.add_column(
        "veeam_machine_backup_snapshots",
        sa.Column("machine_ip", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "veeam_machine_backup_snapshots",
        sa.Column("normalized_machine_ip", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_veeam_machine_backup_snapshots_normalized_machine_ip",
        "veeam_machine_backup_snapshots",
        ["normalized_machine_ip"],
        unique=False,
    )
    op.drop_constraint("uq_veeam_machine_backup_snapshots_normalized_machine_name", "veeam_machine_backup_snapshots")
    op.create_unique_constraint(
        "uq_veeam_machine_backup_snapshots_normalized_machine_name",
        "veeam_machine_backup_snapshots",
        ["normalized_machine_name"],
    )


def downgrade() -> None:
    """Remove machine_ip columns."""
    op.drop_index(
        "ix_veeam_machine_backup_snapshots_normalized_machine_ip",
        "veeam_machine_backup_snapshots",
    )
    op.drop_column("veeam_machine_backup_snapshots", "normalized_machine_ip")
    op.drop_column("veeam_machine_backup_snapshots", "machine_ip")
    op.drop_constraint("uq_veeam_machine_backup_snapshots_normalized_machine_name", "veeam_machine_backup_snapshots")
    op.create_unique_constraint(
        "uq_veeam_machine_backup_snapshots_normalized_machine_name",
        "veeam_machine_backup_snapshots",
        ["normalized_machine_name"],
    )
