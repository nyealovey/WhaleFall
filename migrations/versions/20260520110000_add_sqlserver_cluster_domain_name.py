"""Add SQL Server cluster domain name.

Revision ID: 20260520110000
Revises: 20260520090000
Create Date: 2026-05-20

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260520110000"
down_revision = "20260520090000"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Execute upgrade migration."""
    columns = _column_names("sqlserver_clusters")
    if "domain_name" not in columns:
        op.add_column("sqlserver_clusters", sa.Column("domain_name", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Execute downgrade migration."""
    columns = _column_names("sqlserver_clusters")
    if "domain_name" in columns:
        op.drop_column("sqlserver_clusters", "domain_name")
