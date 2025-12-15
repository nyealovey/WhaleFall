"""Add assigned_at column to account_classification_assignments

Revision ID: 9b3c2f1e8b70
Revises: 5b697a863a79
Create Date: 2025-12-15 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9b3c2f1e8b70"
down_revision = "5b697a863a79"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add assigned_at with timezone and default now()."""

    op.add_column(
        "account_classification_assignments",
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("NOW()"),
        ),
    )
    # 现有行使用 server_default 已填充, 去除默认防止后续写入依赖 DB 时间
    op.alter_column(
        "account_classification_assignments",
        "assigned_at",
        server_default=None,
    )
    op.alter_column(
        "account_classification_assignments",
        "assigned_at",
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("account_classification_assignments", "assigned_at")
