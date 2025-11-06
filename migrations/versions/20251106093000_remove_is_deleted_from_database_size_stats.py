"""移除 database_size_stats 中的删除标记

Revision ID: 20251106093000
Revises: 20251106090000
Create Date: 2025-11-06 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251106093000'
down_revision = '20251106090000'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('database_size_stats') as batch_op:
        batch_op.drop_column('is_deleted')
        batch_op.drop_column('deleted_at')


def downgrade() -> None:
    with op.batch_alter_table('database_size_stats') as batch_op:
        batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    # 移除 server_default 避免影响后续写入
    with op.batch_alter_table('database_size_stats') as batch_op:
        batch_op.alter_column('is_deleted', server_default=None)
