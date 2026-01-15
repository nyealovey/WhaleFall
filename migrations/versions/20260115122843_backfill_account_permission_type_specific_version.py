"""Backfill account_permission.type_specific version.

Revision ID: 20260115122843
Revises: 20260115122054
Create Date: 2026-01-15 12:28:44.746730

"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "20260115122843"
down_revision = "20260115122054"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    # Notes:
    # - `type_specific` is a JSON column. We cast to jsonb for mutation and cast back to json.
    # - Only backfill object payloads missing `version` to avoid accidental rewrites.
    op.execute(
        """
        UPDATE account_permission
        SET type_specific = jsonb_set(type_specific::jsonb, '{version}', '1'::jsonb, true)::json
        WHERE type_specific IS NOT NULL
          AND jsonb_typeof(type_specific::jsonb) = 'object'
          AND NOT (type_specific::jsonb ? 'version')
        """
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    # Best-effort rollback: remove version key when it equals 1.
    op.execute(
        """
        UPDATE account_permission
        SET type_specific = (type_specific::jsonb - 'version')::json
        WHERE type_specific IS NOT NULL
          AND jsonb_typeof(type_specific::jsonb) = 'object'
          AND (type_specific::jsonb ->> 'version') = '1'
        """
    )
