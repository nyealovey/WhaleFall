"""remove tag description and sort order columns

Revision ID: 20251208090000_remove_tag_description_and_sort_order
Revises: 20251109090000_add_is_locked_to_account_permission
Create Date: 2025-12-08 09:00:00
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251208090000_remove_tag_description_and_sort_order"
down_revision = "20251109090000_add_is_locked_to_account_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.drop_column("description")
        batch_op.drop_column("sort_order")


def downgrade() -> None:
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "sort_order",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
            )
        )

    op.execute("UPDATE tags SET sort_order = 0 WHERE sort_order IS NULL")

    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column("sort_order", server_default=None)
