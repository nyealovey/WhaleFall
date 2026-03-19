"""Add JumpServer source binding and asset snapshots.

Revision ID: 20260319103000
Revises: 20260318150000
Create Date: 2026-03-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260319103000"
down_revision = "20260318150000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "jumpserver_source_bindings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(length=512), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_sync_run_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], name="fk_jumpserver_source_binding_credential_id"),
        sa.UniqueConstraint("credential_id", name="uq_jumpserver_source_binding_credential_id"),
    )

    op.create_table(
        "jumpserver_asset_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("db_type", sa.String(length=50), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column(
            "raw_payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("sync_run_id", sa.String(length=64), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("external_id", name="uq_jumpserver_asset_snapshot_external_id"),
    )

    op.create_index(
        "ix_jumpserver_asset_snapshots_db_type_host_port",
        "jumpserver_asset_snapshots",
        ["db_type", "host", "port"],
    )
    op.create_index(
        "ix_jumpserver_asset_snapshots_external_id",
        "jumpserver_asset_snapshots",
        ["external_id"],
    )
    op.create_index(
        "ix_jumpserver_asset_snapshots_synced_at",
        "jumpserver_asset_snapshots",
        ["synced_at"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_jumpserver_asset_snapshots_synced_at", table_name="jumpserver_asset_snapshots")
    op.drop_index("ix_jumpserver_asset_snapshots_external_id", table_name="jumpserver_asset_snapshots")
    op.drop_index("ix_jumpserver_asset_snapshots_db_type_host_port", table_name="jumpserver_asset_snapshots")
    op.drop_table("jumpserver_asset_snapshots")
    op.drop_table("jumpserver_source_bindings")
