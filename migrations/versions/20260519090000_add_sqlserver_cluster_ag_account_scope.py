"""Add SQL Server cluster AG account scope.

Revision ID: 20260519090000
Revises: 20260513120000
Create Date: 2026-05-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260519090000"
down_revision = "20260513120000"
branch_labels = None
depends_on = None


def _constraint_names(table_name: str, kind: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if kind == "unique":
        return {item["name"] for item in inspector.get_unique_constraints(table_name) if item.get("name")}
    if kind == "foreignkey":
        return {item["name"] for item in inspector.get_foreign_keys(table_name) if item.get("name")}
    return set()


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {item["name"] for item in inspector.get_indexes(table_name) if item.get("name")}


def _drop_unique_if_exists(table_name: str, constraint_name: str) -> None:
    if constraint_name in _constraint_names(table_name, "unique"):
        op.drop_constraint(constraint_name, table_name, type_="unique")


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    if index_name in _index_names(table_name):
        op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "sqlserver_clusters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("name", name="uq_sqlserver_clusters_name"),
    )
    op.create_index("ix_sqlserver_clusters_name", "sqlserver_clusters", ["name"])

    op.create_table(
        "sqlserver_cluster_instances",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["cluster_id"], ["sqlserver_clusters.id"]),
        sa.ForeignKeyConstraint(["instance_id"], ["instances.id"]),
        sa.UniqueConstraint("cluster_id", "instance_id", name="uq_sqlserver_cluster_instance"),
        sa.UniqueConstraint("instance_id", name="uq_sqlserver_cluster_instance_instance_id"),
    )
    op.create_index("ix_sqlserver_cluster_instances_cluster_id", "sqlserver_cluster_instances", ["cluster_id"])
    op.create_index("ix_sqlserver_cluster_instances_instance_id", "sqlserver_cluster_instances", ["instance_id"])

    op.create_table(
        "sqlserver_availability_groups",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("cluster_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("listener_name", sa.String(length=255), nullable=True),
        sa.Column("listener_host", sa.String(length=255), nullable=False),
        sa.Column("listener_port", sa.Integer(), nullable=False, server_default="1433"),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("connection_database", sa.String(length=255), nullable=True),
        sa.Column("contained_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_sync_status", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["cluster_id"], ["sqlserver_clusters.id"]),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"]),
        sa.UniqueConstraint("cluster_id", "name", name="uq_sqlserver_ag_cluster_name"),
    )
    op.create_index("ix_sqlserver_availability_groups_cluster_id", "sqlserver_availability_groups", ["cluster_id"])
    op.create_index(
        "ix_sqlserver_ag_cluster_contained",
        "sqlserver_availability_groups",
        ["cluster_id", "contained_enabled", "is_enabled"],
    )

    _add_owner_columns("instance_accounts")
    _add_owner_columns("account_permission")
    _add_owner_columns("account_change_log")

    op.execute("UPDATE instance_accounts SET owner_type = 'instance', owner_id = instance_id WHERE owner_id IS NULL")
    op.execute("UPDATE account_permission SET owner_type = 'instance', owner_id = instance_id WHERE owner_id IS NULL")
    op.execute("UPDATE account_change_log SET owner_type = 'instance', owner_id = instance_id WHERE owner_id IS NULL")

    _drop_unique_if_exists("instance_accounts", "uq_instance_account_instance_username")
    _drop_index_if_exists("account_permission", "uq_current_account_sync")

    op.create_unique_constraint(
        "uq_instance_account_owner_username",
        "instance_accounts",
        ["owner_type", "owner_id", "db_type", "username"],
    )
    op.create_unique_constraint(
        "uq_account_permission_owner",
        "account_permission",
        ["owner_type", "owner_id", "db_type", "username"],
    )
    op.create_index("ix_instance_accounts_owner", "instance_accounts", ["owner_type", "owner_id"])
    op.create_index("ix_instance_accounts_instance_username", "instance_accounts", ["instance_id", "db_type", "username"])
    op.create_index("idx_account_permission_owner", "account_permission", ["owner_type", "owner_id"])
    op.create_index("idx_account_permission_instance_username", "account_permission", ["instance_id", "db_type", "username"])
    op.create_index("idx_account_change_log_owner_time", "account_change_log", ["owner_type", "owner_id", "change_time"])


def downgrade() -> None:
    """Execute downgrade migration."""
    duplicate_count = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT instance_id, db_type, username
                FROM instance_accounts
                GROUP BY instance_id, db_type, username
                HAVING COUNT(*) > 1
            ) AS duplicate_accounts
            """
        )
    ).scalar()
    if int(duplicate_count or 0) > 0:
        raise RuntimeError("Cannot downgrade AG account scope while duplicate instance usernames exist")

    _drop_unique_if_exists("account_permission", "uq_account_permission_owner")
    _drop_unique_if_exists("instance_accounts", "uq_instance_account_owner_username")
    for table_name, index_name in (
        ("account_change_log", "idx_account_change_log_owner_time"),
        ("account_permission", "idx_account_permission_instance_username"),
        ("account_permission", "idx_account_permission_owner"),
        ("instance_accounts", "ix_instance_accounts_instance_username"),
        ("instance_accounts", "ix_instance_accounts_owner"),
    ):
        _drop_index_if_exists(table_name, index_name)

    op.create_unique_constraint(
        "uq_instance_account_instance_username",
        "instance_accounts",
        ["instance_id", "db_type", "username"],
    )
    op.create_index("uq_current_account_sync", "account_permission", ["instance_id", "db_type", "username"], unique=True)

    _drop_owner_columns("account_change_log")
    _drop_owner_columns("account_permission")
    _drop_owner_columns("instance_accounts")

    op.drop_index("ix_sqlserver_ag_cluster_contained", table_name="sqlserver_availability_groups")
    op.drop_index("ix_sqlserver_availability_groups_cluster_id", table_name="sqlserver_availability_groups")
    op.drop_table("sqlserver_availability_groups")
    op.drop_index("ix_sqlserver_cluster_instances_instance_id", table_name="sqlserver_cluster_instances")
    op.drop_index("ix_sqlserver_cluster_instances_cluster_id", table_name="sqlserver_cluster_instances")
    op.drop_table("sqlserver_cluster_instances")
    op.drop_index("ix_sqlserver_clusters_name", table_name="sqlserver_clusters")
    op.drop_table("sqlserver_clusters")


def _add_owner_columns(table_name: str) -> None:
    op.add_column(
        table_name,
        sa.Column("owner_type", sa.String(length=32), nullable=False, server_default="instance"),
    )
    op.add_column(table_name, sa.Column("owner_id", sa.Integer(), nullable=True))
    op.add_column(table_name, sa.Column("cluster_id", sa.Integer(), nullable=True))
    op.add_column(table_name, sa.Column("availability_group_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        f"fk_{table_name}_cluster_id",
        table_name,
        "sqlserver_clusters",
        ["cluster_id"],
        ["id"],
    )
    op.create_foreign_key(
        f"fk_{table_name}_availability_group_id",
        table_name,
        "sqlserver_availability_groups",
        ["availability_group_id"],
        ["id"],
    )
    op.create_index(f"ix_{table_name}_owner_id", table_name, ["owner_id"])
    op.create_index(f"ix_{table_name}_cluster_id", table_name, ["cluster_id"])
    op.create_index(f"ix_{table_name}_availability_group_id", table_name, ["availability_group_id"])


def _drop_owner_columns(table_name: str) -> None:
    for index_name in (
        f"ix_{table_name}_availability_group_id",
        f"ix_{table_name}_cluster_id",
        f"ix_{table_name}_owner_id",
    ):
        _drop_index_if_exists(table_name, index_name)
    for constraint_name in (
        f"fk_{table_name}_availability_group_id",
        f"fk_{table_name}_cluster_id",
    ):
        if constraint_name in _constraint_names(table_name, "foreignkey"):
            op.drop_constraint(constraint_name, table_name, type_="foreignkey")
    op.drop_column(table_name, "availability_group_id")
    op.drop_column(table_name, "cluster_id")
    op.drop_column(table_name, "owner_id")
    op.drop_column(table_name, "owner_type")
