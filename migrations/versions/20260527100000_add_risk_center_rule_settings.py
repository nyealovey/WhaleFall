"""Add risk center rule settings.

Revision ID: 20260527100000
Revises: 20260526150000
Create Date: 2026-05-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260527100000"
down_revision = "20260526150000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "risk_center_rule_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("rule_key", name="uq_risk_center_rule_settings_rule_key"),
    )
    op.create_index("ix_risk_center_rule_settings_rule_key", "risk_center_rule_settings", ["rule_key"])


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_risk_center_rule_settings_rule_key", table_name="risk_center_rule_settings")
    op.drop_table("risk_center_rule_settings")
