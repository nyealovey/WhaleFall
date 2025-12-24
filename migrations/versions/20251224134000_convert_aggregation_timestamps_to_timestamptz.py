"""聚合表时间字段迁移为 timestamptz(UTC).

Revision ID: 20251224134000
Revises: 20251224120000
Create Date: 2025-12-24

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20251224134000"
down_revision = "20251224120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """执行升级迁移.

    背景: DB 侧 `timestamp without time zone` 无法表达时区语义,与 ORM 的
    `DateTime(timezone=True)` 存在漂移,在跨时区/不同客户端解释时容易产生偏移。

    本迁移将聚合表的 `calculated_at/created_at` 统一迁移为 `timestamptz`,
    并将历史数据按 UTC 解释后写入(使用 `AT TIME ZONE 'UTC'`).

    Returns:
        None: 升级迁移执行完成后返回.

    """
    for table_name in ("database_size_aggregations", "instance_size_aggregations"):
        for column_name in ("calculated_at", "created_at"):
            op.alter_column(
                table_name,
                column_name,
                type_=sa.DateTime(timezone=True),
                existing_type=sa.DateTime(timezone=False),
                existing_nullable=False,
                postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            )


def downgrade() -> None:
    """执行降级迁移.

    将 `timestamptz` 回退为 `timestamp without time zone`,回退过程按 UTC
    取回不带时区的时间值(使用 `AT TIME ZONE 'UTC'`).

    Returns:
        None: 降级迁移执行完成后返回.

    """
    for table_name in ("database_size_aggregations", "instance_size_aggregations"):
        for column_name in ("calculated_at", "created_at"):
            op.alter_column(
                table_name,
                column_name,
                type_=sa.DateTime(timezone=False),
                existing_type=sa.DateTime(timezone=True),
                existing_nullable=False,
                postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
            )

