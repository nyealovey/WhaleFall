"""Add email alert settings and events tables.

Revision ID: 20260127110000
Revises: 20260126160000
Create Date: 2026-01-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260127110000"
down_revision = "20260126160000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "email_alert_settings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("global_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "recipients_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
        sa.Column("database_capacity_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("database_capacity_percent_threshold", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("database_capacity_absolute_gb_threshold", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("account_sync_failure_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("database_sync_failure_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("privileged_account_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    settings_table = sa.table(
        "email_alert_settings",
        sa.column("id", sa.Integer()),
        sa.column("global_enabled", sa.Boolean()),
        sa.column("recipients_json", sa.JSON()),
        sa.column("database_capacity_enabled", sa.Boolean()),
        sa.column("database_capacity_percent_threshold", sa.Integer()),
        sa.column("database_capacity_absolute_gb_threshold", sa.Integer()),
        sa.column("account_sync_failure_enabled", sa.Boolean()),
        sa.column("database_sync_failure_enabled", sa.Boolean()),
        sa.column("privileged_account_enabled", sa.Boolean()),
    )
    op.bulk_insert(
        settings_table,
        [
            {
                "id": 1,
                "global_enabled": False,
                "recipients_json": [],
                "database_capacity_enabled": False,
                "database_capacity_percent_threshold": 30,
                "database_capacity_absolute_gb_threshold": 20,
                "account_sync_failure_enabled": False,
                "database_sync_failure_enabled": False,
                "privileged_account_enabled": False,
            },
        ],
    )

    op.create_table(
        "email_alert_events",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("alert_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=True),
        sa.Column("database_name", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column(
            "payload_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("digest_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("alert_type", "bucket_date", "dedupe_key", name="uq_email_alert_events_dedupe"),
    )
    op.create_index("ix_email_alert_events_alert_type", "email_alert_events", ["alert_type"])
    op.create_index("ix_email_alert_events_occurred_at", "email_alert_events", ["occurred_at"])
    op.create_index("ix_email_alert_events_instance_id", "email_alert_events", ["instance_id"])
    op.create_index("ix_email_alert_events_run_id", "email_alert_events", ["run_id"])
    op.create_index("ix_email_alert_events_session_id", "email_alert_events", ["session_id"])
    op.create_index("ix_email_alert_events_bucket_date", "email_alert_events", ["bucket_date"])
    op.create_index("ix_email_alert_events_digest_sent_at", "email_alert_events", ["digest_sent_at"])


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_email_alert_events_digest_sent_at", table_name="email_alert_events")
    op.drop_index("ix_email_alert_events_bucket_date", table_name="email_alert_events")
    op.drop_index("ix_email_alert_events_session_id", table_name="email_alert_events")
    op.drop_index("ix_email_alert_events_run_id", table_name="email_alert_events")
    op.drop_index("ix_email_alert_events_instance_id", table_name="email_alert_events")
    op.drop_index("ix_email_alert_events_occurred_at", table_name="email_alert_events")
    op.drop_index("ix_email_alert_events_alert_type", table_name="email_alert_events")
    op.drop_table("email_alert_events")
    op.drop_table("email_alert_settings")
