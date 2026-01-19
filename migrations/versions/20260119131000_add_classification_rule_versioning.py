"""Add immutable versioning fields to classification_rules.

Revision ID: 20260119131000
Revises: 20260119130000
Create Date: 2026-01-19

"""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260119131000"
down_revision = "20260119130000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column("classification_rules", sa.Column("rule_group_id", sa.String(length=36), nullable=True))
    op.add_column("classification_rules", sa.Column("rule_version", sa.Integer(), nullable=True))
    op.add_column("classification_rules", sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))

    conn = op.get_bind()
    rules = sa.table(
        "classification_rules",
        sa.column("id", sa.Integer()),
        sa.column("rule_group_id", sa.String(length=36)),
        sa.column("rule_version", sa.Integer()),
    )

    rows = conn.execute(sa.select(rules.c.id)).fetchall()
    for (rule_id,) in rows:
        conn.execute(
            sa.update(rules)
            .where(rules.c.id == rule_id)
            .values(rule_group_id=str(uuid4()), rule_version=1),
        )

    op.alter_column("classification_rules", "rule_group_id", existing_type=sa.String(length=36), nullable=False)
    op.alter_column("classification_rules", "rule_version", existing_type=sa.Integer(), nullable=False)

    op.create_unique_constraint(
        "uq_classification_rules_group_version",
        "classification_rules",
        ["rule_group_id", "rule_version"],
    )
    op.create_index(
        "ix_classification_rules_rule_group_id",
        "classification_rules",
        ["rule_group_id"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_classification_rules_rule_group_id", table_name="classification_rules")
    op.drop_constraint("uq_classification_rules_group_version", "classification_rules", type_="unique")
    op.drop_column("classification_rules", "superseded_at")
    op.drop_column("classification_rules", "rule_version")
    op.drop_column("classification_rules", "rule_group_id")

