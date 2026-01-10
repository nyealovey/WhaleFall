"""调度器任务写服务.

职责:
- 更新内置定时任务的触发器配置
- 不依赖 form_service，不做数据库 commit（路由层 safe_route_call 会统一提交/回滚）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from apscheduler.triggers.cron import CronTrigger

from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import NotFoundError, SystemError, ValidationError
from app.scheduler import get_scheduler
from app.types import MutablePayloadDict, PayloadMapping, ResourceIdentifier, SupportsResourceId
from app.utils.structlog_config import log_error, log_info

if TYPE_CHECKING:
    from apscheduler.job import Job
    from apscheduler.schedulers.base import BaseScheduler
else:  # pragma: no cover - 避免运行时导入开销
    Job = BaseScheduler = object  # type: ignore[assignment]

CRON_PARTS_WITH_YEAR = 7
CRON_PARTS_WITH_SECONDS = 6
CRON_PARTS_WITHOUT_SECONDS = 5


@dataclass(slots=True)
class SchedulerJobResource(SupportsResourceId):
    """封装调度器任务上下文并暴露统一的 id 属性."""

    scheduler: BaseScheduler
    job: Job
    id: ResourceIdentifier = field(init=False)

    def __post_init__(self) -> None:
        """根据 `job.id` 设置资源 id."""
        if not hasattr(self.job, "id"):
            raise ValidationError("任务对象缺少 id")
        self.id = str(self.job.id)


class SchedulerJobWriteService:
    """定时任务触发器写服务."""

    def load(self, resource_id: ResourceIdentifier) -> SchedulerJobResource:
        """加载调度器任务资源."""
        job_id = str(resource_id)
        scheduler = cast("BaseScheduler | None", get_scheduler())
        if scheduler is None or not scheduler.running:
            log_error("调度器未启动,无法加载任务", module="scheduler")
            raise SystemError("调度器未启动")

        job = scheduler.get_job(job_id)
        if not job:
            raise NotFoundError("任务不存在")

        return SchedulerJobResource(scheduler=scheduler, job=job)

    def upsert(self, payload: PayloadMapping, resource: SchedulerJobResource | None = None) -> SchedulerJobResource:
        """更新调度器任务触发器."""
        if resource is None:
            raise NotFoundError("任务不存在")

        job = resource.job
        if str(job.id) not in BUILTIN_TASK_IDS:
            raise ValidationError("只能修改内置任务的触发器", message_key="FORBIDDEN")

        sanitized: MutablePayloadDict = dict(payload)
        trigger_type_value = sanitized.get("trigger_type")
        if not isinstance(trigger_type_value, str):
            raise ValidationError("缺少触发器类型配置", message_key="VALIDATION_ERROR")
        trigger_type = trigger_type_value.strip()
        if not trigger_type:
            raise ValidationError("缺少触发器类型配置", message_key="VALIDATION_ERROR")
        if trigger_type != "cron":
            raise ValidationError("仅支持 cron 触发器", message_key="VALIDATION_ERROR")

        trigger = self._build_trigger(trigger_type, sanitized)
        if trigger is None:
            raise ValidationError("无效的触发器配置", message_key="VALIDATION_ERROR")

        try:
            resource.scheduler.modify_job(job.id, trigger=trigger)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            log_error("更新任务触发器失败", module="scheduler", job_id=str(job.id), error=str(exc))
            raise ValidationError("更新任务触发器失败", extra={"exception": str(exc)}) from exc

        updated_job = resource.scheduler.get_job(job.id)
        next_run = getattr(updated_job, "next_run_time", None)
        log_info(
            "内置任务触发器更新成功",
            module="scheduler",
            job_id=str(job.id),
            next_run_time=str(next_run) if next_run else None,
        )
        return resource

    def _build_trigger(self, trigger_type: str, data: PayloadMapping) -> CronTrigger | None:
        if trigger_type != "cron":
            return None
        return self._build_cron_trigger(data)

    def _build_cron_trigger(self, data: PayloadMapping) -> CronTrigger | None:
        cron_kwargs = self._collect_cron_fields(data)
        if not cron_kwargs:
            return None

        try:
            return CronTrigger(timezone="Asia/Shanghai", **cron_kwargs)
        except (ValueError, TypeError) as exc:
            log_error("CronTrigger 构建失败", module="scheduler", error=str(exc))
            return None

    def _collect_cron_fields(self, data: PayloadMapping) -> dict[str, str]:
        parts = self._split_cron_expression(data)
        if len(parts) == CRON_PARTS_WITH_YEAR:
            second, minute, hour, day, month, day_of_week, year = parts
            return {
                "second": second,
                "minute": minute,
                "hour": hour,
                "day": day,
                "month": month,
                "day_of_week": day_of_week,
                "year": year,
            }
        if len(parts) == CRON_PARTS_WITH_SECONDS:
            second, minute, hour, day, month, day_of_week = parts
            return {
                "second": second,
                "minute": minute,
                "hour": hour,
                "day": day,
                "month": month,
                "day_of_week": day_of_week,
            }
        if len(parts) == CRON_PARTS_WITHOUT_SECONDS:
            minute, hour, day, month, day_of_week = parts
            return {
                "second": "0",
                "minute": minute,
                "hour": hour,
                "day": day,
                "month": month,
                "day_of_week": day_of_week,
            }
        raise ValidationError("cron_expression 格式非法", message_key="VALIDATION_ERROR")

    @staticmethod
    def _split_cron_expression(data: PayloadMapping) -> list[str]:
        expr_value = data.get("cron_expression")
        if not isinstance(expr_value, str):
            raise ValidationError("缺少 cron_expression", message_key="VALIDATION_ERROR")
        expr = expr_value.strip()
        if not expr:
            raise ValidationError("缺少 cron_expression", message_key="VALIDATION_ERROR")
        return expr.split()
