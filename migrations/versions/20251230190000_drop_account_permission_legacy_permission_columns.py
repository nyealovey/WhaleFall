"""删除 account_permission legacy 权限列.

Revision ID: 20251230190000
Revises: 20251230183000
Create Date: 2025-12-30

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251230190000"
down_revision = "20251230183000"
branch_labels = None
depends_on = None


LEGACY_PERMISSION_COLUMNS: tuple[str, ...] = (
    "global_privileges",
    "database_privileges",
    "predefined_roles",
    "role_attributes",
    "database_privileges_pg",
    "tablespace_privileges",
    "server_roles",
    "server_permissions",
    "database_roles",
    "database_permissions",
    "oracle_roles",
    "system_privileges",
    "tablespace_privileges_oracle",
)


def upgrade() -> None:
    """执行升级迁移.

    Phase 7: 仅保留 v4 snapshot/facts, 删除旧的按 db_type 固定列.
    """
    for column_name in LEGACY_PERMISSION_COLUMNS:
        op.drop_column("account_permission", column_name)


def downgrade() -> None:
    """执行降级迁移.

    仅用于紧急回滚: 重新添加 legacy 权限列(均为 nullable JSONB).
    """
    for column_name in reversed(LEGACY_PERMISSION_COLUMNS):
        op.add_column(
            "account_permission",
            sa.Column(column_name, postgresql.JSONB(), nullable=True),
        )

