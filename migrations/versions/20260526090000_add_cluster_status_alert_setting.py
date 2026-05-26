"""Add cluster status alert setting.

Revision ID: 20260526090000
Revises: 20260525100000
Create Date: 2026-05-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260526090000"
down_revision = "20260525100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column(
        "email_alert_settings",
        sa.Column("cluster_status_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("email_alert_settings", "cluster_status_enabled")
