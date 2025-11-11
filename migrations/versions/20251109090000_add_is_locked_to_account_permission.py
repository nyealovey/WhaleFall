"""add is_locked column to account_permission

Revision ID: 20251109090000_add_is_locked_to_account_permission
Revises: 20251107100000_add_rule_id_to_account_classification_assignments
Create Date: 2025-11-09 09:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251109090000_add_is_locked_to_account_permission"
down_revision = "20251107100000_add_rule_id_to_account_classification_assignments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "account_permission",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_account_permission_is_locked",
        "account_permission",
        ["is_locked"],
    )

    # 回填锁定状态：依据不同数据库类型的 type_specific 字段推导
    op.execute(
        """
        UPDATE account_permission
        SET is_locked = TRUE
        WHERE
            (db_type = 'mysql' AND COALESCE((type_specific->>'is_locked')::boolean, FALSE) = TRUE)
            OR (db_type = 'postgresql' AND COALESCE((type_specific->>'can_login')::boolean, TRUE) = FALSE)
            OR (db_type = 'sqlserver' AND COALESCE((type_specific->>'is_disabled')::boolean, FALSE) = TRUE)
            OR (db_type = 'oracle' AND COALESCE(upper(type_specific->>'account_status'), 'OPEN') <> 'OPEN')
        """
    )

    op.alter_column(
        "account_permission",
        "is_locked",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_index("ix_account_permission_is_locked", table_name="account_permission")
    op.drop_column("account_permission", "is_locked")
