"""Backfill account_change_log diff payload version.

Revision ID: 20260115123302
Revises: 20260115122843
Create Date: 2026-01-15 12:33:03.872584

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260115123302"
down_revision = "20260115122843"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    # Notes:
    # - `privilege_diff` / `other_diff` are JSON columns. We cast to jsonb for mutation and cast back to json.
    # - Only backfill legacy array payloads; object payloads are treated as already-versioned (or invalid).
    op.execute(
        """
        UPDATE account_change_log
        SET privilege_diff = jsonb_build_object('version', 1, 'entries', privilege_diff::jsonb)::json
        WHERE privilege_diff IS NOT NULL
          AND jsonb_typeof(privilege_diff::jsonb) = 'array'
        """
    )
    op.execute(
        """
        UPDATE account_change_log
        SET other_diff = jsonb_build_object('version', 1, 'entries', other_diff::jsonb)::json
        WHERE other_diff IS NOT NULL
          AND jsonb_typeof(other_diff::jsonb) = 'array'
        """
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    # Best-effort rollback: unwrap v1 object payloads back to legacy list.
    op.execute(
        """
        UPDATE account_change_log
        SET privilege_diff = (privilege_diff::jsonb -> 'entries')::json
        WHERE privilege_diff IS NOT NULL
          AND jsonb_typeof(privilege_diff::jsonb) = 'object'
          AND (privilege_diff::jsonb ->> 'version') = '1'
        """
    )
    op.execute(
        """
        UPDATE account_change_log
        SET other_diff = (other_diff::jsonb -> 'entries')::json
        WHERE other_diff IS NOT NULL
          AND jsonb_typeof(other_diff::jsonb) = 'object'
          AND (other_diff::jsonb ->> 'version') = '1'
        """
    )
