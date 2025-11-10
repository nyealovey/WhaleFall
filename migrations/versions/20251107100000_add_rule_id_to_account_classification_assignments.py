"""add rule_id to account_classification_assignments

Revision ID: 20251107100000_add_rule_id_to_account_classification_assignments
Revises: 20251106093000_remove_is_deleted_from_database_size_stats
Create Date: 2025-11-07 10:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251107100000_add_rule_id_to_account_classification_assignments"
down_revision = "20251106093000_remove_is_deleted_from_database_size_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "account_classification_assignments",
        sa.Column("rule_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_account_classification_assignments_rule_id",
        "account_classification_assignments",
        "classification_rules",
        ["rule_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_account_classification_assignments_rule_id",
        "account_classification_assignments",
        type_="foreignkey",
    )
    op.drop_column("account_classification_assignments", "rule_id")
