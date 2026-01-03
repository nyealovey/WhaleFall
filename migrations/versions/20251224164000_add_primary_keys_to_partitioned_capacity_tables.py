"""为容量分区表父表补齐主键约束.

Revision ID: 20251224164000
Revises: 20251224152000
Create Date: 2025-12-24

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251224164000"
down_revision = "20251224152000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级迁移.

    PostgreSQL 分区表的 `PRIMARY KEY/UNIQUE` 必须包含分区键,否则无法在父表层面保证全局唯一性.
    本迁移为容量域两张分区父表补齐复合主键,以与 ORM 假设对齐并优化基于 `id` 的回表/关联查询.

    Returns:
        None: 升级迁移执行完成后返回.

    """
    # database_size_stats: PARTITION BY RANGE (collected_date)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'database_size_stats_pkey'
                  AND conrelid = 'public.database_size_stats'::regclass
            ) THEN
                ALTER TABLE public.database_size_stats
                    ADD CONSTRAINT database_size_stats_pkey PRIMARY KEY (id, collected_date);
            END IF;
        END$$;
        """,
    )

    # database_size_aggregations: PARTITION BY RANGE (period_start)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'database_size_aggregations_pkey'
                  AND conrelid = 'public.database_size_aggregations'::regclass
            ) THEN
                ALTER TABLE public.database_size_aggregations
                    ADD CONSTRAINT database_size_aggregations_pkey PRIMARY KEY (id, period_start);
            END IF;
        END$$;
        """,
    )


def downgrade() -> None:
    """执行降级迁移.

    Returns:
        None: 降级迁移执行完成后返回.

    """
    op.execute("ALTER TABLE public.database_size_stats DROP CONSTRAINT IF EXISTS database_size_stats_pkey")
    op.execute(
        "ALTER TABLE public.database_size_aggregations DROP CONSTRAINT IF EXISTS database_size_aggregations_pkey"
    )
