"""add sqlserver cluster status sync summary

Revision ID: 20260525080000
Revises: 20260525060000
Create Date: 2026-05-25 08:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260525080000"
down_revision = "20260525060000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sqlserver_clusters", sa.Column("last_status_sync_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("sqlserver_clusters", sa.Column("last_status_sync_status", sa.String(length=32), nullable=True))
    op.add_column("sqlserver_clusters", sa.Column("last_status_sync_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sqlserver_clusters", "last_status_sync_error")
    op.drop_column("sqlserver_clusters", "last_status_sync_status")
    op.drop_column("sqlserver_clusters", "last_status_sync_at")
