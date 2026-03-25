"""Add verify_ssl to jumpserver source bindings.

Revision ID: 20260325002000
Revises: 20260319103000
Create Date: 2026-03-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260325002000"
down_revision = "20260319103000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column("jumpserver_source_bindings", sa.Column("verify_ssl", sa.Boolean(), nullable=True))


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("jumpserver_source_bindings", "verify_ssl")
