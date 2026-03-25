"""Add org_id to jumpserver source bindings.

Revision ID: 20260325005500
Revises: 20260325002000
Create Date: 2026-03-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260325005500"
down_revision = "20260325002000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column("jumpserver_source_bindings", sa.Column("org_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_column("jumpserver_source_bindings", "org_id")
