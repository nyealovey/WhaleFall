"""统一 sync_sessions.status 默认值与约束.

Revision ID: 20251224152000
Revises: 20251224134000
Create Date: 2025-12-24

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20251224152000"
down_revision = "20251224134000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级迁移.

    背景:
    - ORM 历史默认值曾为 `pending`,但 DB 默认值为 `running`,且 DB `CHECK` 约束不接纳 `pending`.
    - 为避免写入失败与语义漂移,本迁移统一 DB 侧默认值与 `CHECK` 约束集合,并做数据修正.

    Returns:
        None: 升级迁移执行完成后返回.

    """
    # 兼容旧数据: 若历史写入过 pending,统一修正为 running,避免后续重建 CHECK 失败.
    op.execute("UPDATE sync_sessions SET status = 'running' WHERE status = 'pending'")

    op.alter_column(
        "sync_sessions",
        "status",
        existing_type=sa.String(20),
        existing_nullable=False,
        server_default=sa.text("'running'"),
    )

    # 统一 CHECK 约束集合(与代码侧 SyncSessionStatus 保持一致)
    op.execute("ALTER TABLE sync_sessions DROP CONSTRAINT IF EXISTS sync_sessions_status_check")
    op.create_check_constraint(
        "sync_sessions_status_check",
        "sync_sessions",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    """执行降级迁移.

    降级仍保留默认值 `running` 与相同的状态集合 `CHECK`,避免出现可回滚但不可用的状态漂移.

    Returns:
        None: 降级迁移执行完成后返回.

    """
    op.alter_column(
        "sync_sessions",
        "status",
        existing_type=sa.String(20),
        existing_nullable=False,
        server_default=sa.text("'running'"),
    )

    op.execute("ALTER TABLE sync_sessions DROP CONSTRAINT IF EXISTS sync_sessions_status_check")
    op.create_check_constraint(
        "sync_sessions_status_check",
        "sync_sessions",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )

