"""Add task runs tables.

Revision ID: 20260120120000
Revises: 20260119132000
Create Date: 2026-01-20

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260120120000"
down_revision = "20260119132000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Execute upgrade migration."""
    op.create_table(
        "task_runs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("task_key", sa.String(length=128), nullable=False),
        sa.Column("task_name", sa.String(length=255), nullable=False),
        sa.Column("task_category", sa.String(length=50), nullable=False),
        sa.Column("trigger_source", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'running'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("progress_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "summary_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("result_url", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("run_id", name="uq_task_runs_run_id"),
    )

    op.create_index("ix_task_runs_run_id", "task_runs", ["run_id"], unique=True)
    op.create_index("ix_task_runs_task_key", "task_runs", ["task_key"])
    op.create_index("ix_task_runs_task_category", "task_runs", ["task_category"])
    op.create_index("ix_task_runs_trigger_source", "task_runs", ["trigger_source"])
    op.create_index("ix_task_runs_status", "task_runs", ["status"])
    op.create_index("ix_task_runs_started_at", "task_runs", ["started_at"])
    op.create_index("ix_task_runs_task_key_started_at", "task_runs", ["task_key", "started_at"])
    op.create_check_constraint(
        "task_runs_status_check",
        "task_runs",
        "status IN ('running', 'completed', 'failed', 'cancelled')",
    )

    op.create_table(
        "task_run_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("item_key", sa.String(length=128), nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=True),
        sa.Column("instance_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metrics_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "details_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["task_runs.run_id"], name="fk_task_run_items_run_id"),
        sa.UniqueConstraint("run_id", "item_type", "item_key", name="uq_task_run_items_run_type_key"),
    )

    op.create_index("ix_task_run_items_run_id", "task_run_items", ["run_id"])
    op.create_index("ix_task_run_items_item_type", "task_run_items", ["item_type"])
    op.create_index("ix_task_run_items_item_key", "task_run_items", ["item_key"])
    op.create_index("ix_task_run_items_instance_id", "task_run_items", ["instance_id"])
    op.create_index("ix_task_run_items_status", "task_run_items", ["status"])
    op.create_index("ix_task_run_items_run_id_status", "task_run_items", ["run_id", "status"])
    op.create_check_constraint(
        "task_run_items_status_check",
        "task_run_items",
        "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_constraint("task_run_items_status_check", "task_run_items", type_="check")
    op.drop_index("ix_task_run_items_run_id_status", table_name="task_run_items")
    op.drop_index("ix_task_run_items_status", table_name="task_run_items")
    op.drop_index("ix_task_run_items_instance_id", table_name="task_run_items")
    op.drop_index("ix_task_run_items_item_key", table_name="task_run_items")
    op.drop_index("ix_task_run_items_item_type", table_name="task_run_items")
    op.drop_index("ix_task_run_items_run_id", table_name="task_run_items")
    op.drop_table("task_run_items")

    op.drop_constraint("task_runs_status_check", "task_runs", type_="check")
    op.drop_index("ix_task_runs_task_key_started_at", table_name="task_runs")
    op.drop_index("ix_task_runs_started_at", table_name="task_runs")
    op.drop_index("ix_task_runs_status", table_name="task_runs")
    op.drop_index("ix_task_runs_trigger_source", table_name="task_runs")
    op.drop_index("ix_task_runs_task_category", table_name="task_runs")
    op.drop_index("ix_task_runs_task_key", table_name="task_runs")
    op.drop_index("ix_task_runs_run_id", table_name="task_runs")
    op.drop_table("task_runs")
