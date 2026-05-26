"""Allow SQL Server AG metadata without listener.

Revision ID: 20260526150000
Revises: 20260526130000
Create Date: 2026-05-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260526150000"
down_revision = "20260526130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    with op.batch_alter_table("sqlserver_availability_groups") as batch_op:
        batch_op.alter_column(
            "listener_host",
            existing_type=sa.String(length=255),
            nullable=True,
        )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.execute("UPDATE sqlserver_availability_groups SET listener_host = '' WHERE listener_host IS NULL")
    with op.batch_alter_table("sqlserver_availability_groups") as batch_op:
        batch_op.alter_column(
            "listener_host",
            existing_type=sa.String(length=255),
            nullable=False,
        )
