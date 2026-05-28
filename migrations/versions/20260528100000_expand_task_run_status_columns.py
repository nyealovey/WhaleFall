"""Expand task run status columns.

Revision ID: 20260528100000
Revises: 20260527100000
Create Date: 2026-05-28

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260528100000"
down_revision = "20260527100000"
branch_labels = None
depends_on = None

_TASK_RUN_STATUSES = ("pending", "running", "completed", "completed_with_errors", "failed", "cancelled")
_OLD_TASK_RUN_STATUSES = ("running", "completed", "failed", "cancelled")
_OLD_TASK_RUN_ITEM_STATUSES = ("pending", "running", "completed", "failed", "cancelled")


def _status_check(statuses: tuple[str, ...]) -> str:
    values = ", ".join(f"'{status}'" for status in statuses)
    return f"status IN ({values})"


def upgrade() -> None:
    """Execute upgrade migration."""
    op.drop_constraint("task_run_items_status_check", "task_run_items", type_="check")
    op.drop_constraint("task_runs_status_check", "task_runs", type_="check")

    op.alter_column(
        "task_runs",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
        existing_server_default=sa.text("'running'"),
    )
    op.alter_column(
        "task_run_items",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.String(length=32),
        existing_nullable=False,
        existing_server_default=sa.text("'pending'"),
    )

    op.create_check_constraint("task_runs_status_check", "task_runs", _status_check(_TASK_RUN_STATUSES))
    op.create_check_constraint("task_run_items_status_check", "task_run_items", _status_check(_TASK_RUN_STATUSES))


def downgrade() -> None:
    """Execute downgrade migration."""
    op.drop_constraint("task_run_items_status_check", "task_run_items", type_="check")
    op.drop_constraint("task_runs_status_check", "task_runs", type_="check")

    op.execute(
        sa.text(
            "UPDATE task_run_items "
            "SET status = 'failed' "
            "WHERE status = 'completed_with_errors'"
        )
    )
    op.execute(sa.text("UPDATE task_runs SET status = 'failed' WHERE status IN ('pending', 'completed_with_errors')"))

    op.alter_column(
        "task_run_items",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'pending'"),
    )
    op.alter_column(
        "task_runs",
        "status",
        existing_type=sa.String(length=32),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'running'"),
    )

    op.create_check_constraint("task_runs_status_check", "task_runs", _status_check(_OLD_TASK_RUN_STATUSES))
    op.create_check_constraint(
        "task_run_items_status_check",
        "task_run_items",
        _status_check(_OLD_TASK_RUN_ITEM_STATUSES),
    )
