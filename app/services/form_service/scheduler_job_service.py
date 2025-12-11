"""定时任务表单服务.

提供内置定时任务触发器的编辑功能,支持 Cron、Interval 和 Date 三种触发器类型.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast
from zoneinfo import ZoneInfo

try:
    from apscheduler.exceptions import APSchedulerError  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - 兼容 APScheduler 4.x
    try:
        from apscheduler.exc import SchedulerError as APSchedulerError  # type: ignore[reportMissingImports]
    except ModuleNotFoundError:
        APSchedulerError = Exception  # type: ignore[misc]

from apscheduler.job import Job
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import NotFoundError, SystemError, ValidationError
from app.scheduler import get_scheduler
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
from app.types import MutablePayloadDict, PayloadMapping, ResourceIdentifier, SupportsResourceId
from app.types.converters import as_int, as_optional_str, as_str
from app.utils.time_utils import time_utils
from app.utils.structlog_config import log_error, log_info

CRON_PARTS_WITH_YEAR = 7
CRON_PARTS_WITH_SECONDS = 6
CRON_PARTS_WITHOUT_SECONDS = 5

TriggerUnion = CronTrigger | IntervalTrigger | DateTrigger

@dataclass(slots=True)
class SchedulerJobResource(SupportsResourceId):
    """封装调度器任务上下文并暴露统一的 id 属性."""

    scheduler: BaseScheduler
    job: Job
    id: ResourceIdentifier = field(init=False)

    def __post_init__(self) -> None:
        self.id = str(getattr(self.job, "id", ""))


class SchedulerJobFormService(BaseResourceService[SchedulerJobResource]):
    """定时任务表单服务.

    负责内置任务触发器的编辑,支持 Cron、Interval 和 Date 三种触发器类型.

    Attributes:
        model: 占位模型,不会持久化到数据库.

    Example:
        >>> service = SchedulerJobFormService()
        >>> result = service.upsert({'trigger_type': 'cron', 'cron_expression': '0 0 * * *'}, resource)
        >>> result.success
        True

    """

    model = SchedulerJobResource  # 占位,不会持久化

    def sanitize(self, payload: PayloadMapping) -> MutablePayloadDict:
        """清理表单数据.

        Args:
            payload: 原始表单数据.

        Returns:
            清理后的数据字典.

        """
        return dict(payload or {})

    def load(self, resource_id: ResourceIdentifier) -> SchedulerJobResource:
        """加载定时任务.

        从调度器中获取指定 ID 的任务及调度器实例.

        Args:
            resource_id: 任务 ID.

        Returns:
            包含 job 和 scheduler 的字典.

        Raises:
            SystemError: 调度器未启动时抛出.
            NotFoundError: 任务不存在时抛出.

        """
        job_id = str(resource_id)
        scheduler = cast("BaseScheduler | None", get_scheduler())
        if scheduler is None or not scheduler.running:
            log_error("调度器未启动,无法加载任务", module="scheduler")
            msg = "调度器未启动"
            raise SystemError(msg)

        job = scheduler.get_job(job_id)
        if not job:
            msg = "任务不存在"
            raise NotFoundError(msg)

        return SchedulerJobResource(scheduler=scheduler, job=job)

    def validate(self, data: MutablePayloadDict, *, resource: SchedulerJobResource | None) -> ServiceResult[MutablePayloadDict]:
        """校验触发器配置是否合法.

        Args:
            data: 清洗后的表单数据.
            resource: 包含 scheduler/job 的上下文.

        Returns:
            ServiceResult: 成功时携带构造好的 trigger.

        """
        job = resource.job if resource else None
        if job is None:
            return ServiceResult.fail("任务不存在", message_key="NOT_FOUND")

        if job.id not in BUILTIN_TASK_IDS:
            return ServiceResult.fail("只能修改内置任务的触发器", message_key="FORBIDDEN")

        trigger_type = data.get("trigger_type")
        if not trigger_type:
            return ServiceResult.fail("缺少触发器类型配置", message_key="VALIDATION_ERROR")

        trigger = self._build_trigger(data)
        if trigger is None:
            return ServiceResult.fail("无效的触发器配置", message_key="VALIDATION_ERROR")

        payload = cast("MutablePayloadDict", {"trigger": trigger})
        return ServiceResult.ok(payload)

    def assign(self, instance: SchedulerJobResource, data: MutablePayloadDict) -> None:
        """将新的触发器应用到调度器.

        Args:
            instance: 包含 scheduler 与 job 的上下文字典.
            data: 校验阶段生成的触发器数据.

        Returns:
            None: 任务触发器更新完成后返回.

        """
        scheduler = instance.scheduler
        job = instance.job
        trigger = cast("TriggerUnion", data["trigger"])
        scheduler.modify_job(job.id, trigger=trigger)

    def after_save(self, instance: SchedulerJobResource, data: MutablePayloadDict) -> None:
        """触发器更新后的善后处理,负责记录下一次执行时间.

        Args:
            instance: 包含 scheduler/job 的上下文.
            data: 校验阶段生成的触发器数据.

        Returns:
            None: 日志记录完成后返回.

        """
        del data
        job = instance.job
        scheduler = instance.scheduler
        updated_job = scheduler.get_job(job.id)
        next_run = getattr(updated_job, "next_run_time", None)
        log_info(
            "内置任务触发器更新成功",
            module="scheduler",
            job_id=job.id,
            next_run_time=str(next_run) if next_run else None,
        )

    def upsert(self, payload: PayloadMapping, resource: SchedulerJobResource | None = None) -> ServiceResult[SchedulerJobResource]:
        """更新内置任务的触发器配置.

        Args:
            payload: 原始表单数据.
            resource: 包含 scheduler/job 的上下文.

        Returns:
            ServiceResult[dict[str, Any]]: 成功时返回上下文,失败时返回错误信息.

        """
        sanitized = self.sanitize(payload)
        validation = self.validate(sanitized, resource=resource)
        if not validation.success:
            return ServiceResult.fail(validation.message or "验证失败", message_key=validation.message_key, extra=validation.extra)

        if resource is None:
            return ServiceResult.fail("任务不存在", message_key="NOT_FOUND")

        try:
            self.assign(resource, validation.data or sanitized)
        except ValidationError:
            raise
        except (APSchedulerError, ValueError) as exc:
            log_error("更新任务触发器失败", module="scheduler", job_id=resource.job.id, error=str(exc))
            return ServiceResult.fail("更新任务触发器失败", extra={"exception": str(exc)})

        self.after_save(resource, validation.data or sanitized)
        return ServiceResult.ok(resource)

    def _build_trigger(self, data: PayloadMapping) -> CronTrigger | IntervalTrigger | DateTrigger | None:
        """根据表单数据构建 APScheduler 触发器.

        Args:
            data: 表单数据.

        Returns:
            CronTrigger | IntervalTrigger | DateTrigger | None: 构建成功返回触发器,否则返回 None.

        """
        trigger_type = as_str(data.get("trigger_type"), default="").strip()

        if trigger_type == "cron":
            cron_kwargs: dict[str, str] = {}
            expr = as_str(data.get("cron_expression"), default="").strip()
            parts: list[str] = expr.split() if expr else []

            def pick(*keys: str) -> str | None:
                for key in keys:
                    candidate = as_optional_str(data.get(key))
                    if candidate:
                        return candidate
                return None

            second = pick("cron_second", "second")
            minute = pick("cron_minute", "minute")
            hour = pick("cron_hour", "hour")
            day = pick("cron_day", "day")
            month = pick("cron_month", "month")
            day_of_week = pick("cron_weekday", "cron_day_of_week", "day_of_week", "weekday")
            year = pick("year")

            if len(parts) == CRON_PARTS_WITH_YEAR:
                second, minute, hour, day, month, day_of_week, year = [
                    pick_value or part
                    for pick_value, part in zip(
                        [second, minute, hour, day, month, day_of_week, year],
                        parts,
                        strict=False,
                    )
                ]
            elif len(parts) == CRON_PARTS_WITH_SECONDS:
                second, minute, hour, day, month, day_of_week = [
                    pick_value or part
                    for pick_value, part in zip(
                        [second, minute, hour, day, month, day_of_week],
                        parts,
                        strict=False,
                    )
                ]
            elif len(parts) == CRON_PARTS_WITHOUT_SECONDS:
                minute, hour, day, month, day_of_week = [
                    pick_value or part
                    for pick_value, part in zip(
                        [minute, hour, day, month, day_of_week],
                        parts,
                        strict=False,
                    )
                ]

            if year is not None:
                cron_kwargs["year"] = year
            if month is not None:
                cron_kwargs["month"] = month
            if day is not None:
                cron_kwargs["day"] = day
            if day_of_week is not None:
                cron_kwargs["day_of_week"] = day_of_week
            if hour is not None:
                cron_kwargs["hour"] = hour
            if minute is not None:
                cron_kwargs["minute"] = minute
            if second is not None:
                cron_kwargs["second"] = second

            try:
                return CronTrigger(timezone=ZoneInfo("Asia/Shanghai"), **cron_kwargs)
            except (ValueError, TypeError) as exc:
                log_error("CronTrigger 构建失败", module="scheduler", error=str(exc))
                return None

        if trigger_type == "interval":
            interval_kwargs: dict[str, int] = {}
            for key in ["weeks", "days", "hours", "minutes", "seconds"]:
                converted = as_int(data.get(key))
                if not converted or converted <= 0:
                    continue
                interval_kwargs[key] = converted
            if not interval_kwargs:
                return None
            try:
                return IntervalTrigger(**interval_kwargs)
            except (ValueError, TypeError) as exc:
                log_error("IntervalTrigger 构建失败", module="scheduler", error=str(exc))
                return None

        if trigger_type == "date":
            run_date = as_optional_str(data.get("run_date"))
            if not run_date:
                return None
            dt = None
            dt = time_utils.to_utc(run_date)
            if dt is None:
                log_error(
                    "DateTrigger 运行时间解析失败",
                    module="scheduler",
                    raw_value=run_date,
                )
                return None
            try:
                return DateTrigger(run_date=dt)
            except (ValueError, TypeError) as exc:
                log_error("DateTrigger 构建失败", module="scheduler", error=str(exc))
                return None

        return None
