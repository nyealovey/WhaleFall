"""Add Veeam source binding and machine backup snapshots.

Revision ID: 20260325063000
Revises: 20260319103000
Create Date: 2026-03-25

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260325063000"
down_revision = "20260325005500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "veeam_source_bindings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("server_host", sa.String(length=255), nullable=False),
        sa.Column("server_port", sa.Integer(), nullable=False),
        sa.Column("api_version", sa.String(length=32), nullable=False),
        sa.Column("verify_ssl", sa.Boolean(), nullable=True),
        sa.Column(
            "match_domains",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_sync_run_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], name="fk_veeam_source_binding_credential_id"),
        sa.UniqueConstraint("credential_id", name="uq_veeam_source_binding_credential_id"),
    )

    op.create_table(
        "veeam_machine_backup_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("machine_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_machine_name", sa.String(length=255), nullable=False),
        sa.Column("latest_backup_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("job_name", sa.String(length=255), nullable=True),
        sa.Column("restore_point_name", sa.String(length=255), nullable=True),
        sa.Column("source_record_id", sa.String(length=255), nullable=True),
        sa.Column(
            "raw_payload",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("sync_run_id", sa.String(length=64), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("normalized_machine_name", name="uq_veeam_machine_backup_snapshot_machine_name"),
    )

    op.create_index(
        "ix_veeam_machine_backup_snapshots_latest_backup_at",
        "veeam_machine_backup_snapshots",
        ["latest_backup_at"],
    )
    op.create_index(
        "ix_veeam_machine_backup_snapshots_normalized_machine_name",
        "veeam_machine_backup_snapshots",
        ["normalized_machine_name"],
    )
    op.create_index(
        "ix_veeam_machine_backup_snapshots_synced_at",
        "veeam_machine_backup_snapshots",
        ["synced_at"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_veeam_machine_backup_snapshots_synced_at", table_name="veeam_machine_backup_snapshots")
    op.drop_index(
        "ix_veeam_machine_backup_snapshots_normalized_machine_name",
        table_name="veeam_machine_backup_snapshots",
    )
    op.drop_index("ix_veeam_machine_backup_snapshots_latest_backup_at", table_name="veeam_machine_backup_snapshots")
    op.drop_table("veeam_machine_backup_snapshots")
    op.drop_table("veeam_source_bindings")
