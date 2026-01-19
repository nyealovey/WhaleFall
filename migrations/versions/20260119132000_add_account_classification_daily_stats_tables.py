"""Add account classification daily stats tables.

Revision ID: 20260119132000
Revises: 20260119131000
Create Date: 2026-01-19

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260119132000"
down_revision = "20260119131000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "account_classification_daily_rule_match_stats",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("classification_id", sa.Integer(), nullable=False),
        sa.Column("db_type", sa.String(length=20), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("matched_accounts_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["rule_id"],
            ["classification_rules.id"],
            name="fk_ac_daily_rule_match_rule_id",
        ),
        sa.ForeignKeyConstraint(
            ["classification_id"],
            ["account_classifications.id"],
            name="fk_ac_daily_rule_match_classification_id",
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["instances.id"],
            name="fk_ac_daily_rule_match_instance_id",
        ),
        sa.UniqueConstraint(
            "stat_date",
            "rule_id",
            "db_type",
            "instance_id",
            name="uq_ac_daily_rule_match_key",
        ),
    )
    op.create_index(
        "ix_ac_daily_rule_match_classification_date",
        "account_classification_daily_rule_match_stats",
        ["classification_id", "stat_date"],
    )
    op.create_index(
        "ix_ac_daily_rule_match_rule_date",
        "account_classification_daily_rule_match_stats",
        ["rule_id", "stat_date"],
    )

    op.create_table(
        "account_classification_daily_classification_match_stats",
        sa.Column("id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("classification_id", sa.Integer(), nullable=False),
        sa.Column("db_type", sa.String(length=20), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("matched_accounts_distinct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["classification_id"],
            ["account_classifications.id"],
            name="fk_ac_daily_classification_match_classification_id",
        ),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["instances.id"],
            name="fk_ac_daily_classification_match_instance_id",
        ),
        sa.UniqueConstraint(
            "stat_date",
            "classification_id",
            "db_type",
            "instance_id",
            name="uq_ac_daily_classification_match_key",
        ),
    )
    op.create_index(
        "ix_ac_daily_classification_match_classification_date",
        "account_classification_daily_classification_match_stats",
        ["classification_id", "stat_date"],
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index(
        "ix_ac_daily_classification_match_classification_date",
        table_name="account_classification_daily_classification_match_stats",
    )
    op.drop_table("account_classification_daily_classification_match_stats")

    op.drop_index("ix_ac_daily_rule_match_rule_date", table_name="account_classification_daily_rule_match_stats")
    op.drop_index(
        "ix_ac_daily_rule_match_classification_date",
        table_name="account_classification_daily_rule_match_stats",
    )
    op.drop_table("account_classification_daily_rule_match_stats")

