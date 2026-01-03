"""Drop legacy status columns from account_permission and add capabilities index.

Revision ID: 20251231120000
Revises: 20251230211000
Create Date: 2025-12-31

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20251231120000"
down_revision = "20251230211000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.execute('DROP INDEX IF EXISTS "ix_account_permission_is_locked"')
    op.drop_column("account_permission", "is_superuser")
    op.drop_column("account_permission", "is_locked")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_account_permission_facts_capabilities "
        "ON account_permission USING gin ((permission_facts->'capabilities'))",
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.execute("DROP INDEX IF EXISTS idx_account_permission_facts_capabilities")
    op.add_column("account_permission", sa.Column("is_superuser", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column(
        "account_permission",
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.execute('CREATE INDEX IF NOT EXISTS "ix_account_permission_is_locked" ON account_permission (is_locked)')
