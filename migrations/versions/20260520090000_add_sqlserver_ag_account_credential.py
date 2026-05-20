"""Add SQL Server AG account collection credential.

Revision ID: 20260520090000
Revises: 20260519090000
Create Date: 2026-05-20

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260520090000"
down_revision = "20260519090000"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {item["name"] for item in inspector.get_indexes(table_name) if item.get("name")}


def _foreign_key_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {item["name"] for item in inspector.get_foreign_keys(table_name) if item.get("name")}


def upgrade() -> None:
    """Execute upgrade migration."""
    columns = _column_names("sqlserver_availability_groups")
    if "account_credential_id" not in columns:
        op.add_column("sqlserver_availability_groups", sa.Column("account_credential_id", sa.Integer(), nullable=True))

    fk_names = _foreign_key_names("sqlserver_availability_groups")
    if "fk_sqlserver_ag_account_credential_id" not in fk_names:
        op.create_foreign_key(
            "fk_sqlserver_ag_account_credential_id",
            "sqlserver_availability_groups",
            "credentials",
            ["account_credential_id"],
            ["id"],
        )

    indexes = _index_names("sqlserver_availability_groups")
    if "ix_sqlserver_ag_account_credential_id" not in indexes:
        op.create_index(
            "ix_sqlserver_ag_account_credential_id",
            "sqlserver_availability_groups",
            ["account_credential_id"],
        )

    op.execute(
        """
        UPDATE sqlserver_availability_groups
        SET credential_id = NULL,
            account_credential_id = NULL,
            is_enabled = false
        """
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    indexes = _index_names("sqlserver_availability_groups")
    if "ix_sqlserver_ag_account_credential_id" in indexes:
        op.drop_index("ix_sqlserver_ag_account_credential_id", table_name="sqlserver_availability_groups")

    fk_names = _foreign_key_names("sqlserver_availability_groups")
    if "fk_sqlserver_ag_account_credential_id" in fk_names:
        op.drop_constraint(
            "fk_sqlserver_ag_account_credential_id",
            "sqlserver_availability_groups",
            type_="foreignkey",
        )

    columns = _column_names("sqlserver_availability_groups")
    if "account_credential_id" in columns:
        op.drop_column("sqlserver_availability_groups", "account_credential_id")
