"""调度器 jobs read API Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做序列化/Response、不 commit
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.core.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.core.constants.sync_constants import SyncCategory
from app.core.exceptions import NotFoundError, SystemError
from app.core.types.scheduler import SchedulerJobDetail, SchedulerJobListItem
from app.repositories.scheduler_jobs_repository import SchedulerJobsRepository
from app.utils.structlog_config import log_error

if TYPE_CHECKING:
    from apscheduler.job import Job
    from apscheduler.schedulers.background import BackgroundScheduler


CRON_FIELD_COUNT = 8
CRON_YEAR_INDEX = 0
CRON_MONTH_INDEX = 1
CRON_DAY_INDEX = 2
CRON_DAY_OF_WEEK_INDEX = 4
CRON_HOUR_INDEX = 5
CRON_MINUTE_INDEX = 6
CRON_SECOND_INDEX = 7


JOB_CATEGORY_MAP: dict[str, str] = {
    "sync_accounts": SyncCategory.ACCOUNT.value,
    "collect_database_sizes": SyncCategory.CAPACITY.value,
    "calculate_database_size_aggregations": SyncCategory.AGGREGATION.value,
}


class SchedulerJobsReadService:
    """调度器任务读取服务."""

    def __init__(self, repository: SchedulerJobsRepository | None = None) -> None:
        """初始化服务并注入仓库."""
        self._repository = repository or SchedulerJobsRepository()

    def list_jobs(self) -> list[SchedulerJobListItem]:
        """列出调度器任务列表."""
        try:
            scheduler = self._repository.ensure_scheduler_running()
            jobs = cast("list[Job]", scheduler.get_jobs())
        except Exception as exc:
            log_error("获取任务列表失败", module="scheduler_jobs_read_service", exception=exc)
            raise SystemError("获取任务列表失败") from exc

        items = [self._build_job_list_item(job, scheduler) for job in jobs]
        items.sort(key=lambda item: item.id)
        return items

    def get_job(self, job_id: str) -> SchedulerJobDetail:
        """获取调度器任务详情."""
        try:
            scheduler = self._repository.ensure_scheduler_running()
            job = scheduler.get_job(job_id)
        except Exception as exc:
            log_error("获取任务详情失败", module="scheduler_jobs_read_service", exception=exc)
            raise SystemError("获取任务详情失败") from exc

        if not job:
            raise NotFoundError("任务不存在")

        return SchedulerJobDetail(
            id=job.id,
            name=job.name,
            next_run_time=(job.next_run_time.isoformat() if job.next_run_time else None),
            trigger=str(job.trigger),
            func=(job.func.__name__ if hasattr(job.func, "__name__") else str(job.func)),
            args=job.args,
            kwargs=job.kwargs,
            misfire_grace_time=job.misfire_grace_time,
            max_instances=job.max_instances,
            coalesce=job.coalesce,
        )

    def _build_job_list_item(self, job: Job, scheduler: BackgroundScheduler) -> SchedulerJobListItem:
        trigger_type, trigger_args = self._collect_trigger_args(job)
        state = "STATE_RUNNING" if scheduler.running and job.next_run_time else "STATE_PAUSED"

        last_run_time = self._repository.lookup_job_last_run(job_name=job.name)
        if not last_run_time:
            category = JOB_CATEGORY_MAP.get(job.id)
            last_run_time = self._repository.resolve_session_last_run(category=category, limit=10)

        return SchedulerJobListItem(
            id=job.id,
            name=job.name,
            description=job.name,
            next_run_time=(job.next_run_time.isoformat() if job.next_run_time else None),
            last_run_time=last_run_time,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            state=state,
            is_builtin=(job.id in BUILTIN_TASK_IDS),
            func=(job.func.__name__ if hasattr(job.func, "__name__") else str(job.func)),
            args=job.args,
            kwargs=job.kwargs,
        )

    @staticmethod
    def _collect_trigger_args(job: Job) -> tuple[str, dict[str, str]]:
        trigger_type = str(type(job.trigger).__name__).lower().replace("trigger", "")
        trigger_args: dict[str, str] = {}

        if trigger_type != "cron" or "CronTrigger" not in str(type(job.trigger)):
            return trigger_type, {"description": str(job.trigger)}

        fields = getattr(job.trigger, "fields", {})
        if isinstance(fields, dict):
            trigger_args["second"] = fields.get("second", "0")
            trigger_args["minute"] = fields.get("minute", "0")
            trigger_args["hour"] = fields.get("hour", "0")
            trigger_args["day"] = fields.get("day", "*")
            trigger_args["month"] = fields.get("month", "*")
            trigger_args["day_of_week"] = fields.get("day_of_week", "*")
            year_value = fields.get("year")
            trigger_args["year"] = "" if year_value is None else str(year_value)
            return trigger_type, trigger_args

        if isinstance(fields, list) and len(fields) >= CRON_FIELD_COUNT:
            trigger_args["second"] = str(fields[CRON_SECOND_INDEX] or "0")
            trigger_args["minute"] = str(fields[CRON_MINUTE_INDEX] or "0")
            trigger_args["hour"] = str(fields[CRON_HOUR_INDEX] or "0")
            trigger_args["day"] = str(fields[CRON_DAY_INDEX] or "*")
            trigger_args["month"] = str(fields[CRON_MONTH_INDEX] or "*")
            trigger_args["day_of_week"] = str(fields[CRON_DAY_OF_WEEK_INDEX] or "*")
            year_value = fields[CRON_YEAR_INDEX]
            trigger_args["year"] = "" if year_value is None else str(year_value)
            return trigger_type, trigger_args

        return trigger_type, {
            "second": "0",
            "minute": "0",
            "hour": "0",
            "day": "*",
            "month": "*",
            "day_of_week": "*",
            "year": "",
        }
