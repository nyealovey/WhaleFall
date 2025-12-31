"""调度器任务写服务.

职责:
- 更新内置定时任务的触发器配置
- 不依赖 form_service，不做数据库 commit（路由层 safe_route_call 会统一提交/回滚）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import NotFoundError, SystemError, ValidationError
from app.scheduler import get_scheduler
from app.types import MutablePayloadDict, PayloadMapping, ResourceIdentifier, SupportsResourceId
from app.types.converters import as_int, as_optional_str, as_str
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

if TYPE_CHECKING:
    from collections.abc import Callable

    from apscheduler.job import Job
    from apscheduler.schedulers.base import BaseScheduler
else:  # pragma: no cover - 避免运行时导入开销
    Job = BaseScheduler = object  # type: ignore[assignment]

TriggerUnion = CronTrigger | IntervalTrigger | DateTrigger

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
        if not hasattr(self.job, "id"):
            raise ValidationError("任务对象缺少 id")
        self.id = str(self.job.id)


class SchedulerJobWriteService:
    """定时任务触发器写服务."""

    def load(self, resource_id: ResourceIdentifier) -> SchedulerJobResource:
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
        if resource is None:
            raise NotFoundError("任务不存在")

        job = resource.job
        if str(job.id) not in BUILTIN_TASK_IDS:
            raise ValidationError("只能修改内置任务的触发器", message_key="FORBIDDEN")

        sanitized: MutablePayloadDict = dict(payload or {})
        trigger_type = as_str(sanitized.get("trigger_type"), default="").strip()
        if not trigger_type:
            raise ValidationError("缺少触发器类型配置", message_key="VALIDATION_ERROR")

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

    def _build_trigger(self, trigger_type: str, data: PayloadMapping) -> TriggerUnion | None:
        builders: dict[str, Callable[[PayloadMapping], TriggerUnion | None]] = {
            "cron": self._build_cron_trigger,
            "interval": self._build_interval_trigger,
            "date": self._build_date_trigger,
        }
        builder = builders.get(trigger_type)
        if builder is None:
            return None
        return cast("TriggerUnion | None", builder(data))

    def _build_cron_trigger(self, data: PayloadMapping) -> TriggerUnion | None:
        cron_kwargs = self._collect_cron_fields(data)
        if not cron_kwargs:
            return None

        timezone_name = as_optional_str(data.get("timezone")) or "Asia/Shanghai"
        try:
            timezone = ZoneInfo(timezone_name)
        except Exception:  # pragma: no cover - zoneinfo 与系统 tzdata 相关
            timezone = ZoneInfo("Asia/Shanghai")

        try:
            return CronTrigger(timezone=timezone, **cron_kwargs)
        except (ValueError, TypeError) as exc:
            log_error("CronTrigger 构建失败", module="scheduler", error=str(exc))
            return None

    def _collect_cron_fields(self, data: PayloadMapping) -> dict[str, str]:
        base_fields = self._extract_cron_base_fields(data)
        parts = self._split_cron_expression(data)
        merged_fields = self._apply_expression_overrides(parts, base_fields)
        return self._build_cron_kwargs(merged_fields)

    def _extract_cron_base_fields(self, data: PayloadMapping) -> dict[str, str | None]:
        return {
            "second": self._pick(data, "cron_second", "second"),
            "minute": self._pick(data, "cron_minute", "minute"),
            "hour": self._pick(data, "cron_hour", "hour"),
            "day": self._pick(data, "cron_day", "day"),
            "month": self._pick(data, "cron_month", "month"),
            "day_of_week": self._pick(data, "cron_weekday", "cron_day_of_week", "day_of_week", "weekday"),
            "year": self._pick(data, "year"),
        }

    @staticmethod
    def _split_cron_expression(data: PayloadMapping) -> list[str]:
        expr = as_str(data.get("cron_expression"), default="").strip()
        return expr.split() if expr else []

    def _apply_expression_overrides(
        self,
        parts: list[str],
        base_fields: dict[str, str | None],
    ) -> dict[str, str | None]:
        if len(parts) == CRON_PARTS_WITH_YEAR:
            (
                base_fields["second"],
                base_fields["minute"],
                base_fields["hour"],
                base_fields["day"],
                base_fields["month"],
                base_fields["day_of_week"],
                base_fields["year"],
            ) = self._merge_parts(parts, list(base_fields.values()))
        elif len(parts) == CRON_PARTS_WITH_SECONDS:
            (
                base_fields["second"],
                base_fields["minute"],
                base_fields["hour"],
                base_fields["day"],
                base_fields["month"],
                base_fields["day_of_week"],
            ) = self._merge_parts(parts, list(base_fields.values())[:6])
        elif len(parts) == CRON_PARTS_WITHOUT_SECONDS:
            (
                base_fields["minute"],
                base_fields["hour"],
                base_fields["day"],
                base_fields["month"],
                base_fields["day_of_week"],
            ) = self._merge_parts(parts, list(base_fields.values())[1:6])
        return base_fields

    @staticmethod
    def _build_cron_kwargs(fields: dict[str, str | None]) -> dict[str, str]:
        return {key: value for key, value in fields.items() if value is not None}

    @staticmethod
    def _pick(data: PayloadMapping, *keys: str) -> str | None:
        for key in keys:
            candidate = as_optional_str(data.get(key))
            if candidate:
                return candidate
        return None

    @staticmethod
    def _merge_parts(parts: list[str], picked: list[str | None]) -> list[str]:
        return [
            pick_value or part
            for pick_value, part in zip(
                picked,
                parts,
                strict=False,
            )
        ]

    def _build_interval_trigger(self, data: PayloadMapping) -> TriggerUnion | None:
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

    def _build_date_trigger(self, data: PayloadMapping) -> TriggerUnion | None:
        run_date = as_optional_str(data.get("run_date"))
        if not run_date:
            return None
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
