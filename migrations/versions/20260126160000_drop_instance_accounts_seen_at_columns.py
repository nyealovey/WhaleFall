"""Drop first/last seen columns from instance_accounts.

Revision ID: 20260126160000
Revises: 20260120150000
Create Date: 2026-01-26

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260126160000"
down_revision = "20260120150000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.execute('DROP INDEX IF EXISTS "ix_instance_accounts_last_seen"')
    op.drop_column("instance_accounts", "first_seen_at")
    op.drop_column("instance_accounts", "last_seen_at")


def downgrade() -> None:
    """Execute downgrade migration."""
    op.add_column(
        "instance_accounts",
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "instance_accounts",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS "ix_instance_accounts_last_seen" ON instance_accounts (last_seen_at)',
    )

