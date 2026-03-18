"""Add instance config snapshots table.

Revision ID: 20260318150000
Revises: 20260318062000
Create Date: 2026-03-18

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260318150000"
down_revision = "20260318062000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "instance_config_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("db_type", sa.String(length=50), nullable=False),
        sa.Column("config_key", sa.String(length=64), nullable=False),
        sa.Column(
            "snapshot",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "facts",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("last_sync_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"], name="fk_instance_config_snapshots_instance_id"),
        sa.UniqueConstraint(
            "instance_id",
            "config_key",
            name="uq_instance_config_snapshot_instance_config_key",
        ),
    )

    op.create_index(
        "ix_instance_config_snapshots_instance_config_key",
        "instance_config_snapshots",
        ["instance_id", "config_key"],
    )
    op.create_index("ix_instance_config_snapshots_config_key", "instance_config_snapshots", ["config_key"])
    op.create_index(
        "ix_instance_config_snapshots_last_sync_time",
        "instance_config_snapshots",
        ["last_sync_time"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_instance_config_snapshots_last_sync_time", table_name="instance_config_snapshots")
    op.drop_index("ix_instance_config_snapshots_config_key", table_name="instance_config_snapshots")
    op.drop_index("ix_instance_config_snapshots_instance_config_key", table_name="instance_config_snapshots")
    op.drop_table("instance_config_snapshots")
