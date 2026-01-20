"""Refactor account_classifications to code + 1-6 risk_level, drop color.

Revision ID: 20260120150000
Revises: 20260120120000
Create Date: 2026-01-20

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260120150000"
down_revision = "20260120120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.alter_column(
        "account_classifications",
        "name",
        new_column_name="code",
        existing_type=sa.String(length=100),
    )
    op.execute("UPDATE account_classifications SET code = lower(code)")

    op.drop_column("account_classifications", "color")

    # risk_level: legacy low/medium/high/critical -> 1-6 (1 highest, 6 lowest)
    # Postgres will try to cast the existing DEFAULT along with the column type.
    # The legacy default is typically `'medium'::varchar`, which can't cast to SMALLINT.
    op.execute("ALTER TABLE account_classifications ALTER COLUMN risk_level DROP DEFAULT")
    op.execute(
        """
        UPDATE account_classifications
        SET risk_level = CASE lower(risk_level)
            WHEN 'critical' THEN '1'
            WHEN 'high' THEN '2'
            WHEN 'medium' THEN '4'
            WHEN 'low' THEN '6'
            ELSE '4'
        END
        """,
    )
    op.alter_column(
        "account_classifications",
        "risk_level",
        existing_type=sa.String(length=20),
        type_=sa.SmallInteger(),
        nullable=False,
        postgresql_using="risk_level::smallint",
    )
    op.alter_column(
        "account_classifications",
        "risk_level",
        existing_type=sa.SmallInteger(),
        server_default=sa.text("4"),
    )
    op.create_check_constraint(
        "account_classifications_risk_level_check",
        "account_classifications",
        "risk_level BETWEEN 1 AND 6",
    )

    # Seed 6 system classifications (code is immutable and used as stable semantic anchor).
    op.execute(
        """
        INSERT INTO account_classifications
            (code, display_name, description, risk_level, icon_name, priority, is_system, is_active)
        VALUES
            ('super', '超高风险', '', 1, 'fa-crown', 100, true, true),
            ('highly', '高风险', '', 2, 'fa-shield-alt', 90, true, true),
            ('sensitive', '敏感', '', 3, 'fa-exclamation-triangle', 80, true, true),
            ('medium', '中风险', '', 4, 'fa-user', 70, true, true),
            ('low', '低风险', '', 5, 'fa-tag', 60, true, true),
            ('public', '公开', '', 6, 'fa-eye', 50, true, true)
        ON CONFLICT (code) DO UPDATE
        SET is_system = true,
            is_active = true,
            risk_level = EXCLUDED.risk_level,
            icon_name = EXCLUDED.icon_name
        """,
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_constraint(
        "account_classifications_risk_level_check",
        "account_classifications",
        type_="check",
    )
    op.execute("ALTER TABLE account_classifications ALTER COLUMN risk_level DROP DEFAULT")
    op.alter_column(
        "account_classifications",
        "risk_level",
        existing_type=sa.SmallInteger(),
        type_=sa.String(length=20),
        nullable=False,
        postgresql_using="""
        CASE risk_level
            WHEN 1 THEN 'critical'
            WHEN 2 THEN 'high'
            WHEN 3 THEN 'high'
            WHEN 4 THEN 'medium'
            WHEN 5 THEN 'low'
            WHEN 6 THEN 'low'
            ELSE 'medium'
        END
        """,
    )
    op.alter_column(
        "account_classifications",
        "risk_level",
        existing_type=sa.String(length=20),
        server_default=sa.text("'medium'"),
    )

    op.add_column(
        "account_classifications",
        sa.Column("color", sa.String(length=20), nullable=True),
    )

    op.alter_column(
        "account_classifications",
        "code",
        new_column_name="name",
        existing_type=sa.String(length=100),
    )
