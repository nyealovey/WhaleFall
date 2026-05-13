"""Support multiple Veeam sources.

Revision ID: 20260513090000
Revises: 20260415090000
Create Date: 2026-05-13

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260513090000"
down_revision = "20260415090000"
branch_labels = None
depends_on = None


def _unique_constraint_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {item["name"] for item in inspector.get_unique_constraints(table_name) if item.get("name")}


def upgrade() -> None:
    """Execute upgrade migration."""
    bind = op.get_bind()

    op.add_column(
        "veeam_source_bindings",
        sa.Column("name", sa.String(length=128), nullable=True),
    )
    op.execute(
        """
        UPDATE veeam_source_bindings AS binding
        SET name = COALESCE(NULLIF(credentials.name, ''), '默认 Veeam')
        FROM credentials
        WHERE credentials.id = binding.credential_id
        """
    )
    op.execute("UPDATE veeam_source_bindings SET name = '默认 Veeam' WHERE name IS NULL OR name = ''")
    op.alter_column("veeam_source_bindings", "name", nullable=False)

    source_constraint_names = _unique_constraint_names("veeam_source_bindings")
    if "uq_veeam_source_binding_credential_id" in source_constraint_names:
        op.drop_constraint(
            "uq_veeam_source_binding_credential_id",
            "veeam_source_bindings",
            type_="unique",
        )

    op.add_column(
        "veeam_machine_backup_snapshots",
        sa.Column("source_binding_id", sa.Integer(), nullable=True),
    )
    first_source_id = bind.execute(sa.text("SELECT id FROM veeam_source_bindings ORDER BY id ASC LIMIT 1")).scalar()
    if first_source_id is not None:
        bind.execute(
            sa.text(
                """
                UPDATE veeam_machine_backup_snapshots
                SET source_binding_id = :source_binding_id
                WHERE source_binding_id IS NULL
                """
            ),
            {"source_binding_id": int(first_source_id)},
        )

    snapshot_constraint_names = _unique_constraint_names("veeam_machine_backup_snapshots")
    for constraint_name in (
        "uq_veeam_machine_backup_snapshot_machine_name",
        "uq_veeam_snapshot_normalized_name",
        "uq_veeam_snapshot_normalized_ip",
    ):
        if constraint_name in snapshot_constraint_names:
            op.drop_constraint(
                constraint_name,
                "veeam_machine_backup_snapshots",
                type_="unique",
            )

    op.alter_column("veeam_machine_backup_snapshots", "source_binding_id", nullable=False)
    op.create_foreign_key(
        "fk_veeam_machine_backup_snapshot_source_binding_id",
        "veeam_machine_backup_snapshots",
        "veeam_source_bindings",
        ["source_binding_id"],
        ["id"],
    )
    op.create_index(
        "ix_veeam_machine_backup_snapshots_source_binding_id",
        "veeam_machine_backup_snapshots",
        ["source_binding_id"],
    )
    op.create_unique_constraint(
        "uq_veeam_snapshot_source_normalized_name",
        "veeam_machine_backup_snapshots",
        ["source_binding_id", "normalized_machine_name"],
    )
    op.create_unique_constraint(
        "uq_veeam_snapshot_source_normalized_ip",
        "veeam_machine_backup_snapshots",
        ["source_binding_id", "normalized_machine_ip"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    duplicate_count = op.get_bind().execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM (
                SELECT normalized_machine_name
                FROM veeam_machine_backup_snapshots
                WHERE normalized_machine_name IS NOT NULL
                GROUP BY normalized_machine_name
                HAVING COUNT(*) > 1
            ) AS duplicate_names
            """
        )
    ).scalar()
    if int(duplicate_count or 0) > 0:
        raise RuntimeError("Cannot downgrade multi-source Veeam snapshots with duplicate machine names")

    op.drop_constraint(
        "uq_veeam_snapshot_source_normalized_ip",
        "veeam_machine_backup_snapshots",
        type_="unique",
    )
    op.drop_constraint(
        "uq_veeam_snapshot_source_normalized_name",
        "veeam_machine_backup_snapshots",
        type_="unique",
    )
    op.drop_index(
        "ix_veeam_machine_backup_snapshots_source_binding_id",
        table_name="veeam_machine_backup_snapshots",
    )
    op.drop_constraint(
        "fk_veeam_machine_backup_snapshot_source_binding_id",
        "veeam_machine_backup_snapshots",
        type_="foreignkey",
    )
    op.drop_column("veeam_machine_backup_snapshots", "source_binding_id")
    op.create_unique_constraint(
        "uq_veeam_snapshot_normalized_name",
        "veeam_machine_backup_snapshots",
        ["normalized_machine_name"],
    )
    op.create_unique_constraint(
        "uq_veeam_snapshot_normalized_ip",
        "veeam_machine_backup_snapshots",
        ["normalized_machine_ip"],
    )
    op.create_unique_constraint(
        "uq_veeam_source_binding_credential_id",
        "veeam_source_bindings",
        ["credential_id"],
    )
    op.drop_column("veeam_source_bindings", "name")
