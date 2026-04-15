"""Add backup issue toggle to email alert settings.

Revision ID: 20260415090000
Revises: 20260403060000
Create Date: 2026-04-15

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260415090000"
down_revision = "20260403060000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column(
        "email_alert_settings",
        sa.Column("backup_issue_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("email_alert_settings", "backup_issue_enabled")
