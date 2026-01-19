"""Add display_name to account_classifications.

Revision ID: 20260119130000
Revises: 20260115123302
Create Date: 2026-01-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260119130000"
down_revision = "20260115123302"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column(
        "account_classifications",
        sa.Column("display_name", sa.String(length=100), nullable=True),
    )
    op.execute("UPDATE account_classifications SET display_name = name WHERE display_name IS NULL")
    op.alter_column("account_classifications", "display_name", existing_type=sa.String(length=100), nullable=False)


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("account_classifications", "display_name")

