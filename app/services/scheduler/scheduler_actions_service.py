"""Scheduler actions service.

将 scheduler namespace 中“动作编排/线程后台执行/循环删除”等逻辑下沉到 service：
- run_job_in_background：启动后台线程执行指定 job
- reload_jobs：删除现有任务并重新加载

路由层仅保留鉴权/CSRF、参数读取与封套响应。
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast

from apscheduler.jobstores.base import JobLookupError
from flask import current_app, has_app_context
from sqlalchemy.exc import SQLAlchemyError

import app.scheduler as scheduler_module
from app import create_app
from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import ConflictError, NotFoundError
from app.infra.route_safety import log_with_context
from app.utils.structlog_config import log_info, log_warning


class SupportsJob(Protocol):
    """Scheduler job protocol (for typing)."""

    func: Callable[..., Any]


class SupportsScheduler(Protocol):
    """Scheduler protocol (for typing)."""

    running: bool

    def get_job(self, job_id: str) -> SupportsJob | None:
        """获取指定任务."""
        ...

    def get_jobs(self) -> Sequence[SupportsJob]:
        """获取当前任务列表."""
        ...

    def remove_job(self, job_id: str) -> None:
        """移除任务."""
        ...

    def pause_job(self, job_id: str) -> None:
        """暂停任务."""
        ...

    def resume_job(self, job_id: str) -> None:
        """恢复任务."""
        ...


@dataclass(frozen=True, slots=True)
class SchedulerJobsReloadResult:
    """调度任务重新加载结果."""

    deleted: list[str]
    reloaded: list[str]
    deleted_count: int
    reloaded_count: int


BACKGROUND_EXECUTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConflictError,
    NotFoundError,
    RuntimeError,
    ValueError,
    LookupError,
    SQLAlchemyError,
)
JOB_REMOVAL_EXCEPTIONS: tuple[type[BaseException], ...] = (JobLookupError, ValueError)


class SchedulerActionsService:
    """调度器动作编排服务."""

    @staticmethod
    def ensure_scheduler_running() -> SupportsScheduler:
        """确保调度器已启动."""
        scheduler = scheduler_module.get_scheduler()
        if scheduler is None or not getattr(scheduler, "running", False):
            log_warning("调度器未启动", module="scheduler")
            raise ConflictError("调度器未启动")
        return cast(SupportsScheduler, scheduler)

    def run_job_in_background(self, *, job_id: str, created_by: int | None) -> str:
        """启动后台线程执行指定任务,返回线程名."""
        scheduler = self.ensure_scheduler_running()
        job = scheduler.get_job(job_id)
        if not job:
            raise NotFoundError("任务不存在")

        log_info("开始立即执行任务", module="scheduler", job_id=job_id, job_name=getattr(job, "name", None))

        def _run_job_in_background(captured_created_by: int | None = created_by) -> None:
            base_app = current_app if has_app_context() else create_app(init_scheduler_on_start=False)
            try:
                with base_app.app_context():
                    if job_id in BUILTIN_TASK_IDS:
                        manual_kwargs: dict[str, Any] = dict(getattr(job, "kwargs", {}) or {})
                        if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                            manual_kwargs["manual_run"] = True
                            manual_kwargs["created_by"] = captured_created_by
                        job.func(*getattr(job, "args", ()), **manual_kwargs)
                    else:
                        job.func(*getattr(job, "args", ()), **(getattr(job, "kwargs", {}) or {}))

                log_info(
                    "任务立即执行成功",
                    module="scheduler",
                    job_id=job_id,
                    job_name=getattr(job, "name", None),
                )
            except BACKGROUND_EXECUTION_EXCEPTIONS as func_error:  # pragma: no cover - defensive log
                log_with_context(
                    "error",
                    "任务函数执行失败",
                    module="scheduler",
                    action="run_job_background",
                    context={"job_id": job_id, "job_name": getattr(job, "name", None)},
                    extra={
                        "error_type": func_error.__class__.__name__,
                        "error_message": str(func_error),
                    },
                )

        thread = threading.Thread(target=_run_job_in_background, name=f"{job_id}_manual", daemon=True)
        thread.start()
        return thread.name

    def reload_jobs(self) -> SchedulerJobsReloadResult:
        """删除当前任务并重新加载所有任务."""
        scheduler = self.ensure_scheduler_running()
        existing_jobs = scheduler.get_jobs()
        existing_job_ids = [cast(str, getattr(job, "id", "")) for job in existing_jobs]

        deleted_count = 0
        for job_id in existing_job_ids:
            try:
                scheduler.remove_job(job_id)
            except JOB_REMOVAL_EXCEPTIONS as del_err:
                log_with_context(
                    "error",
                    "重新加载-删除任务失败",
                    module="scheduler",
                    action="reload_jobs",
                    context={"job_id": job_id},
                    extra={
                        "error_type": del_err.__class__.__name__,
                        "error_message": str(del_err),
                    },
                )
            else:
                deleted_count += 1
                log_info("重新加载-删除任务", module="scheduler", job_id=job_id)

        scheduler_module._reload_all_jobs()

        reloaded_jobs = scheduler.get_jobs()
        reloaded_job_ids = [cast(str, getattr(job, "id", "")) for job in reloaded_jobs]

        log_info(
            "任务重新加载完成",
            module="scheduler",
            deleted_count=deleted_count,
            reloaded_count=len(reloaded_jobs),
        )
        return SchedulerJobsReloadResult(
            deleted=existing_job_ids,
            reloaded=reloaded_job_ids,
            deleted_count=deleted_count,
            reloaded_count=len(reloaded_jobs),
        )
