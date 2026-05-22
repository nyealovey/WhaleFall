"""add ad domain sync fields

Revision ID: 20260521160000
Revises: 20260521130000
Create Date: 2026-05-21 16:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260521160000"
down_revision = "20260521130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ad_domain_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("netbios_name", sa.String(length=64), nullable=False),
        sa.Column("domain_controllers", sa.JSON(), nullable=False),
        sa.Column("ldap_port", sa.Integer(), nullable=False, server_default="636"),
        sa.Column("use_ssl", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("verify_ssl", sa.Boolean(), nullable=True),
        sa.Column("base_dn", sa.String(length=512), nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_sync_run_id", sa.String(length=64), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_ad_domain_configs_netbios_name", "ad_domain_configs", ["netbios_name"])

    with op.batch_alter_table("instance_accounts") as batch_op:
        batch_op.add_column(sa.Column("ad_domain_config_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("ad_disabled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("ad_orphaned_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key(
            "fk_instance_accounts_ad_domain_config_id",
            "ad_domain_configs",
            ["ad_domain_config_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_instance_accounts_ad_status",
            ["ad_domain_config_id", "ad_disabled_at", "ad_orphaned_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("instance_accounts") as batch_op:
        batch_op.drop_index("ix_instance_accounts_ad_status")
        batch_op.drop_constraint("fk_instance_accounts_ad_domain_config_id", type_="foreignkey")
        batch_op.drop_column("ad_orphaned_at")
        batch_op.drop_column("ad_disabled_at")
        batch_op.drop_column("ad_domain_config_id")

    op.drop_index("ix_ad_domain_configs_netbios_name", table_name="ad_domain_configs")
    op.drop_table("ad_domain_configs")
