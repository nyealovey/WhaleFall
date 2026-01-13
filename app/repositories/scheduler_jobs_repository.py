"""调度器任务读模型 Repository.

职责:
- 仅负责 Query 组装与读取(包含 APScheduler 数据访问)
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import SQLAlchemyError

from app.core.constants.sync_constants import SyncOperationType
from app.core.exceptions import ConflictError
from app.models.sync_session import SyncSession
from app.models.unified_log import UnifiedLog
from app.scheduler import get_scheduler
from app.utils.structlog_config import log_warning
from app.utils.time_utils import time_utils


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
    def lookup_job_last_run(*, job_name: str) -> str | None:
        """从日志中查询任务上次运行时间."""
        try:
            recent_log = (
                UnifiedLog.query.filter(
                    UnifiedLog.module == "scheduler",
                    UnifiedLog.message.like(f"%{job_name}%"),
                    UnifiedLog.timestamp >= time_utils.now() - timedelta(days=1),
                )
                .order_by(UnifiedLog.timestamp.desc())
                .first()
            )
            if recent_log:
                return recent_log.timestamp.isoformat()
        except SQLAlchemyError as lookup_error:  # pragma: no cover - 防御性告警
            log_warning(
                "获取任务上次运行时间失败",
                module="scheduler",
                job_name=job_name,
                error=str(lookup_error),
            )
        return None

    @staticmethod
    def resolve_session_last_run(*, category: str | None, limit: int = 10) -> str | None:
        """按同步分类推断上次运行时间.

        约束:
        - 仅使用 completed_at(完成时间), 不做 updated_at/started_at/created_at 回退.
        - 若存在定时任务会话, 优先返回定时任务会话的 completed_at.
        - 否则返回第一条手动会话的 completed_at.
        """
        if not category:
            return None

        sessions = SyncSession.get_sessions_by_category(category, limit=limit)
        manual_fallback: str | None = None
        for session in sessions:
            ts = session.completed_at
            if not ts:
                continue
            if session.sync_type == SyncOperationType.SCHEDULED_TASK.value:
                return ts.isoformat()
            if manual_fallback is None:
                manual_fallback = ts.isoformat()

        return manual_fallback
