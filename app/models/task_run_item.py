"""TaskRunItem 模型.

TaskRunItem 是一次 TaskRun(run) 内的子执行单元（instance/rule/step）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils


class TaskRunItem(db.Model):
    """任务运行子项(item)模型."""

    __tablename__ = "task_run_items"

    __table_args__ = (
        db.UniqueConstraint("run_id", "item_type", "item_key", name="uq_task_run_items_run_type_key"),
        db.Index("ix_task_run_items_run_id_status", "run_id", "status"),
    )

    id = db.Column(db.Integer, primary_key=True)

    run_id = db.Column(
        db.String(36),
        db.ForeignKey("task_runs.run_id"),
        nullable=False,
        index=True,
    )

    item_type = db.Column(db.String(20), nullable=False, index=True)
    item_key = db.Column(db.String(128), nullable=False, index=True)
    item_name = db.Column(db.String(255), nullable=True)

    instance_id = db.Column(db.Integer, nullable=True, index=True)

    status = db.Column(db.String(20), nullable=False, default="pending", index=True)

    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    metrics_json = db.Column(db.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True)
    details_json = db.Column(db.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "item_type": self.item_type,
            "item_key": self.item_key,
            "item_name": self.item_name,
            "instance_id": self.instance_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metrics_json": self.metrics_json,
            "details_json": self.details_json,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
