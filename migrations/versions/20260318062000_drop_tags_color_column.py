"""Drop color from tags.

Revision ID: 20260318062000
Revises: 20260127110000
Create Date: 2026-03-18

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260318062000"
down_revision = "20260127110000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.drop_column("tags", "color")


def downgrade() -> None:
    """Execute downgrade migration."""
    op.add_column(
        "tags",
        sa.Column(
            "color",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'primary'"),
        ),
    )
