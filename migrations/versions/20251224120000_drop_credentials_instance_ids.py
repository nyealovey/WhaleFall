"""删除 credentials.instance_ids 字段.

Revision ID: 20251224120000
Revises: 20251219161048
Create Date: 2025-12-24

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251224120000"
down_revision = "20251219161048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级迁移.

    删除 `credentials.instance_ids` 冗余列.

    Returns:
        None: 升级迁移执行完成后返回.

    """
    op.drop_column("credentials", "instance_ids")


def downgrade() -> None:
    """执行降级迁移.

    恢复 `credentials.instance_ids` 列,仅用于回滚与排障.

    Returns:
        None: 降级迁移执行完成后返回.

    """
    op.add_column(
        "credentials",
        sa.Column("instance_ids", postgresql.JSONB(), nullable=True),
    )
