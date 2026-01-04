"""Add database_table_size_stats table for on-demand table size snapshots.

Revision ID: 20260104120000
Revises: 20251231120100
Create Date: 2026-01-04

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260104120000"
down_revision = "20251231120100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "database_table_size_stats",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(length=255), nullable=False),
        sa.Column("schema_name", sa.String(length=255), nullable=False),
        sa.Column("table_name", sa.String(length=255), nullable=False),
        sa.Column("size_mb", sa.BigInteger(), nullable=False),
        sa.Column("data_size_mb", sa.BigInteger(), nullable=True),
        sa.Column("index_size_mb", sa.BigInteger(), nullable=True),
        sa.Column("row_count", sa.BigInteger(), nullable=True),
        sa.Column(
            "collected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["instances.id"],
            name="fk_database_table_size_stats_instance_id",
        ),
        sa.UniqueConstraint(
            "instance_id",
            "database_name",
            "schema_name",
            "table_name",
            name="uq_database_table_size_stats_key",
        ),
    )
    op.create_index(
        "ix_database_table_size_stats_instance_database",
        "database_table_size_stats",
        ["instance_id", "database_name"],
    )
    op.create_index(
        "ix_database_table_size_stats_instance_database_size",
        "database_table_size_stats",
        ["instance_id", "database_name", "size_mb"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_database_table_size_stats_instance_database_size", table_name="database_table_size_stats")
    op.drop_index("ix_database_table_size_stats_instance_database", table_name="database_table_size_stats")
    op.drop_table("database_table_size_stats")

