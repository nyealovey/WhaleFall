"""Add Feishu alert delivery settings.

Revision ID: 20260513120000
Revises: 20260513090000
Create Date: 2026-05-13

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260513120000"
down_revision = "20260513090000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.add_column(
        "email_alert_settings",
        sa.Column("feishu_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "email_alert_settings",
        sa.Column("feishu_webhook_url_encrypted", sa.Text(), nullable=True),
    )

    op.create_table(
        "email_alert_event_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "details_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["event_id"], ["email_alert_events.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("event_id", "channel", name="uq_email_alert_event_deliveries_event_channel"),
    )
    op.create_index(
        "ix_email_alert_event_deliveries_channel_status",
        "email_alert_event_deliveries",
        ["channel", "status"],
    )
    op.create_index("ix_email_alert_event_deliveries_event_id", "email_alert_event_deliveries", ["event_id"])


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_index("ix_email_alert_event_deliveries_event_id", table_name="email_alert_event_deliveries")
    op.drop_index("ix_email_alert_event_deliveries_channel_status", table_name="email_alert_event_deliveries")
    op.drop_table("email_alert_event_deliveries")
    op.drop_column("email_alert_settings", "feishu_webhook_url_encrypted")
    op.drop_column("email_alert_settings", "feishu_enabled")
