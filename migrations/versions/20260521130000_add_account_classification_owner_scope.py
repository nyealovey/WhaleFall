"""add account classification owner scope

Revision ID: 20260521130000
Revises: 20260520110000
Create Date: 2026-05-21 13:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260521130000"
down_revision = "20260520110000"
branch_labels = None
depends_on = None

RULE_TABLE = "account_classification_daily_rule_match_stats"
CLASSIFICATION_TABLE = "account_classification_daily_classification_match_stats"


def _add_owner_scope_columns(table_name: str) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.add_column(sa.Column("owner_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("owner_id", sa.Integer(), nullable=True))

    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET owner_type = 'instance',
                owner_id = instance_id
            WHERE owner_type IS NULL OR owner_id IS NULL
            """
        )
    )

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column("owner_type", existing_type=sa.String(length=32), nullable=False)
        batch_op.alter_column("owner_id", existing_type=sa.Integer(), nullable=False)


def upgrade() -> None:
    _add_owner_scope_columns(RULE_TABLE)
    _add_owner_scope_columns(CLASSIFICATION_TABLE)

    with op.batch_alter_table(RULE_TABLE) as batch_op:
        batch_op.drop_constraint("uq_ac_daily_rule_match_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_ac_daily_rule_match_key",
            ["stat_date", "rule_id", "db_type", "owner_type", "owner_id"],
        )
        batch_op.create_index("ix_ac_daily_rule_match_owner", ["owner_type", "owner_id"])

    with op.batch_alter_table(CLASSIFICATION_TABLE) as batch_op:
        batch_op.drop_constraint("uq_ac_daily_classification_match_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_ac_daily_classification_match_key",
            ["stat_date", "classification_id", "db_type", "owner_type", "owner_id"],
        )
        batch_op.create_index("ix_ac_daily_classification_match_owner", ["owner_type", "owner_id"])


def downgrade() -> None:
    with op.batch_alter_table(CLASSIFICATION_TABLE) as batch_op:
        batch_op.drop_index("ix_ac_daily_classification_match_owner")
        batch_op.drop_constraint("uq_ac_daily_classification_match_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_ac_daily_classification_match_key",
            ["stat_date", "classification_id", "db_type", "instance_id"],
        )
        batch_op.drop_column("owner_id")
        batch_op.drop_column("owner_type")

    with op.batch_alter_table(RULE_TABLE) as batch_op:
        batch_op.drop_index("ix_ac_daily_rule_match_owner")
        batch_op.drop_constraint("uq_ac_daily_rule_match_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_ac_daily_rule_match_key",
            ["stat_date", "rule_id", "db_type", "instance_id"],
        )
        batch_op.drop_column("owner_id")
        batch_op.drop_column("owner_type")
