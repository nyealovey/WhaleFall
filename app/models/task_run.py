"""TaskRun 模型.

将原 "同步会话中心" 升级为 "通用任务运行中心" 后，TaskRun 作为一次任务执行(run)的统一观测面。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.dialects import postgresql

from app import db
from app.utils.time_utils import time_utils


class TaskRun(db.Model):
    """任务运行(run)模型."""

    __tablename__ = "task_runs"

    __table_args__ = (db.Index("ix_task_runs_task_key_started_at", "task_key", "started_at"),)

    id = db.Column(db.Integer, primary_key=True)

    run_id = db.Column(db.String(36), unique=True, nullable=False, index=True)

    task_key = db.Column(db.String(128), nullable=False, index=True)
    task_name = db.Column(db.String(255), nullable=False)
    task_category = db.Column(db.String(50), nullable=False, index=True)
    trigger_source = db.Column(db.String(20), nullable=False, index=True)

    status = db.Column(db.String(20), nullable=False, default="running", index=True)

    started_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_by = db.Column(db.Integer, nullable=True)

    progress_total = db.Column(db.Integer, nullable=False, default=0)
    progress_completed = db.Column(db.Integer, nullable=False, default=0)
    progress_failed = db.Column(db.Integer, nullable=False, default=0)

    summary_json = db.Column(db.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True)
    result_url = db.Column(db.String(255), nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), default=time_utils.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=time_utils.now, onupdate=time_utils.now)

    items = db.relationship(
        "TaskRunItem",
        primaryjoin="TaskRun.run_id==foreign(TaskRunItem.run_id)",
        backref="run",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "task_key": self.task_key,
            "task_name": self.task_name,
            "task_category": self.task_category,
            "trigger_source": self.trigger_source,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by,
            "progress_total": self.progress_total,
            "progress_completed": self.progress_completed,
            "progress_failed": self.progress_failed,
            "summary_json": self.summary_json,
            "result_url": self.result_url,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
