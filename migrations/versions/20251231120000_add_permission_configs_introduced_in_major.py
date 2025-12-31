"""Add permission_configs.introduced_in_major.

Revision ID: 20251231120000
Revises: 20251230211000
Create Date: 2025-12-31

变更:
- 为 permission_configs 增加 introduced_in_major 字段,用于标识权限项首次引入的数据库大版本.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251231120000"
down_revision = "20251230211000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "permission_configs",
        sa.Column("introduced_in_major", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("permission_configs", "introduced_in_major")

