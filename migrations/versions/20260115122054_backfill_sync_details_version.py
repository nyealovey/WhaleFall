"""Backfill sync_instance_records.sync_details version.

Revision ID: 20260115122054
Revises: 20260104120000
Create Date: 2026-01-15 12:20:56.260330

"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260115122054"
down_revision = "20260104120000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    # Notes:
    # - `sync_details` is a JSON column. We cast to jsonb for mutation and cast back to json.
    # - Only backfill object payloads missing `version` to avoid accidental rewrites.
    op.execute(
        """
        UPDATE sync_instance_records
        SET sync_details = jsonb_set(sync_details::jsonb, '{version}', '1'::jsonb, true)::json
        WHERE sync_details IS NOT NULL
          AND jsonb_typeof(sync_details::jsonb) = 'object'
          AND NOT (sync_details::jsonb ? 'version')
        """
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    # Best-effort rollback: remove version key when it equals 1.
    op.execute(
        """
        UPDATE sync_instance_records
        SET sync_details = (sync_details::jsonb - 'version')::json
        WHERE sync_details IS NOT NULL
          AND jsonb_typeof(sync_details::jsonb) = 'object'
          AND (sync_details::jsonb ->> 'version') = '1'
        """
    )
