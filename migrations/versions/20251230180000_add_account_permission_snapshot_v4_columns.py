"""为 account_permission 增加 v4 snapshot 列.

Revision ID: 20251230180000
Revises: 20251224164000
Create Date: 2025-12-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251230180000"
down_revision = "20251224164000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级迁移.

    为 `account_permission` 增加:
    - `permission_snapshot` (jsonb, nullable)
    - `permission_snapshot_version` (int, default 4)
    """
    op.add_column(
        "account_permission",
        sa.Column("permission_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "account_permission",
        sa.Column(
            "permission_snapshot_version",
            sa.Integer(),
            nullable=False,
            server_default="4",
        ),
    )


def downgrade() -> None:
    """执行降级迁移."""
    op.drop_column("account_permission", "permission_snapshot_version")
    op.drop_column("account_permission", "permission_snapshot")
