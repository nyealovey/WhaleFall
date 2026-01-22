"""调度器任务读模型 Repository.

职责:
- 仅负责 Query 组装与读取(包含 APScheduler 数据访问)
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.exceptions import ConflictError
from app.models.task_run import TaskRun
from app.scheduler import get_scheduler
from app.utils.structlog_config import log_warning
from app.utils.time_utils import UTC_TZ


class SchedulerJobsRepository:
    """调度器任务查询 Repository."""

    def ensure_scheduler_running(self) -> BackgroundScheduler:
        """确保调度器已启动并返回实例."""
        scheduler = get_scheduler()
        if scheduler is None or not scheduler.running:
            log_warning("调度器未启动", module="scheduler")
            raise ConflictError("调度器未启动")
        return scheduler

    @staticmethod
    def lookup_job_last_run(*, job_id: str) -> str | None:
        """从 TaskRun 中查询任务上次运行时间(以 started_at 为准)."""
        latest = (
            TaskRun.query.filter(TaskRun.task_key == job_id)
            .order_by(TaskRun.started_at.desc(), TaskRun.id.desc())
            .first()
        )
        if latest and latest.started_at:
            started_at = latest.started_at
            if isinstance(started_at, datetime) and started_at.tzinfo is None:
                # SQLite 等环境可能丢失 tzinfo; API 输出统一按 UTC 处理。
                started_at = started_at.replace(tzinfo=UTC_TZ)
            return started_at.isoformat()
        return None
