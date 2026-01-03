"""为 account_permission 增加 facts 列并移除 snapshot version 列.

Revision ID: 20251230183000
Revises: 20251230180000
Create Date: 2025-12-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251230183000"
down_revision = "20251230180000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级迁移.

    - 新增 `permission_facts` (jsonb, nullable): 事实层(用于统计/查询)。
    - 移除 `permission_snapshot_version`: 快照 schema 版本以 JSON payload 内的 `version` 为准。
    """
    op.add_column(
        "account_permission",
        sa.Column("permission_facts", postgresql.JSONB(), nullable=True),
    )
    op.drop_column("account_permission", "permission_snapshot_version")


def downgrade() -> None:
    """执行降级迁移."""
    op.add_column(
        "account_permission",
        sa.Column(
            "permission_snapshot_version",
            sa.Integer(),
            nullable=False,
            server_default="4",
        ),
    )
    op.drop_column("account_permission", "permission_facts")
