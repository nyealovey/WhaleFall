"""定时任务表单服务。

提供内置定时任务触发器的编辑功能，支持 Cron、Interval 和 Date 三种触发器类型。
"""

from __future__ import annotations

from typing import Any, Mapping

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import NotFoundError, SystemError, ValidationError
from app.scheduler import get_scheduler
from app.services.form_service.resource_form_service import BaseResourceService, ServiceResult
from app.utils import time_utils
from app.utils.structlog_config import log_error, log_info


class SchedulerJobFormService(BaseResourceService[dict[str, Any]]):
    """定时任务表单服务。

    负责内置任务触发器的编辑，支持 Cron、Interval 和 Date 三种触发器类型。

    Attributes:
        model: 占位模型，不会持久化到数据库。

    Example:
        >>> service = SchedulerJobFormService()
        >>> result = service.upsert({'trigger_type': 'cron', 'cron_expression': '0 0 * * *'}, resource)
        >>> result.success
        True
    """

    model = dict  # 占位，不会持久化

    def sanitize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """清理表单数据。

        Args:
            payload: 原始表单数据。

        Returns:
            清理后的数据字典。
        """
        return dict(payload or {})

    def load(self, job_id: str) -> dict[str, Any]:
        """加载定时任务。

        从调度器中获取指定 ID 的任务及调度器实例。

        Args:
            job_id: 任务 ID。

        Returns:
            包含 job 和 scheduler 的字典。

        Raises:
            SystemError: 调度器未启动时抛出。
            NotFoundError: 任务不存在时抛出。
        """
        scheduler = get_scheduler()  # type: ignore
        if not scheduler.running:
            log_error("调度器未启动，无法加载任务", module="scheduler")
            raise SystemError("调度器未启动")

        job = scheduler.get_job(job_id)
        if not job:
            raise NotFoundError("任务不存在")

        return {"job": job, "scheduler": scheduler}

    def validate(self, data: dict[str, Any], *, resource: dict[str, Any] | None) -> ServiceResult[dict[str, Any]]:
        """校验触发器配置是否合法。

        Args:
            data: 清洗后的表单数据。
            resource: 包含 scheduler/job 的上下文。

        Returns:
            ServiceResult: 成功时携带构造好的 trigger。
        """

        job = resource["job"] if resource else None
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

        return ServiceResult.ok({"trigger": trigger})

    def assign(self, instance: dict[str, Any], data: dict[str, Any]) -> None:
        """将新的触发器应用到调度器。"""

        scheduler = instance["scheduler"]
        job = instance["job"]
        scheduler.modify_job(job.id, trigger=data["trigger"])

    def after_save(self, instance: dict[str, Any], data: dict[str, Any]) -> None:
        """触发器更新后的善后处理，负责记录下一次执行时间。"""

        job = instance["job"]
        scheduler = instance["scheduler"]
        updated_job = scheduler.get_job(job.id)
        next_run = getattr(updated_job, "next_run_time", None)
        log_info(
            "内置任务触发器更新成功",
            module="scheduler",
            job_id=job.id,
            next_run_time=str(next_run) if next_run else None,
        )

    def upsert(self, payload: Mapping[str, Any], resource: dict[str, Any] | None = None) -> ServiceResult[dict[str, Any]]:
        """更新内置任务的触发器配置。"""

        sanitized = self.sanitize(payload)
        validation = self.validate(sanitized, resource=resource)
        if not validation.success:
            return ServiceResult.fail(validation.message or "验证失败", message_key=validation.message_key, extra=validation.extra)

        if resource is None:
            return ServiceResult.fail("任务不存在", message_key="NOT_FOUND")

        try:
            self.assign(resource, validation.data or sanitized)
        except ValidationError as exc:
            raise exc
        except Exception as exc:  # noqa: BLE001
            log_error("更新任务触发器失败", module="scheduler", job_id=resource["job"].id, error=str(exc))
            return ServiceResult.fail("更新任务触发器失败", extra={"exception": str(exc)})

        self.after_save(resource, validation.data or sanitized)
        return ServiceResult.ok(resource)

    def _build_trigger(self, data: Mapping[str, Any]) -> CronTrigger | IntervalTrigger | DateTrigger | None:
        trigger_type = data.get("trigger_type")

        if trigger_type == "cron":
            cron_kwargs: dict[str, Any] = {}
            expr = str(data.get("cron_expression", "")).strip()
            parts: list[str] = expr.split() if expr else []

            def pick(*keys: str) -> Any:
                for key in keys:
                    value = data.get(key)
                    if value is not None and str(value).strip() != "":
                        return value
                return None

            second = pick("cron_second", "second")
            minute = pick("cron_minute", "minute")
            hour = pick("cron_hour", "hour")
            day = pick("cron_day", "day")
            month = pick("cron_month", "month")
            day_of_week = pick("cron_weekday", "cron_day_of_week", "day_of_week", "weekday")
            year = pick("year")

            try:
                if len(parts) == 7:
                    second, minute, hour, day, month, day_of_week, year = [
                        pick_value or part for pick_value, part in zip(
                            [second, minute, hour, day, month, day_of_week, year], parts
                        )
                    ]
                elif len(parts) == 6:
                    second, minute, hour, day, month, day_of_week = [
                        pick_value or part for pick_value, part in zip(
                            [second, minute, hour, day, month, day_of_week], parts
                        )
                    ]
                elif len(parts) == 5:
                    minute, hour, day, month, day_of_week = [
                        pick_value or part for pick_value, part in zip(
                            [minute, hour, day, month, day_of_week], parts
                        )
                    ]
            except Exception:  # noqa: BLE001
                pass

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
                cron_kwargs["timezone"] = "Asia/Shanghai"
                return CronTrigger(**cron_kwargs)
            except Exception as exc:  # noqa: BLE001
                log_error("CronTrigger 构建失败", module="scheduler", error=str(exc))
                return None

        if trigger_type == "interval":
            kwargs: dict[str, int] = {}
            for key in ["weeks", "days", "hours", "minutes", "seconds"]:
                value = data.get(key)
                if value is None or str(value).strip() == "":
                    continue
                try:
                    converted = int(value)
                    if converted > 0:
                        kwargs[key] = converted
                except Exception:  # noqa: BLE001
                    continue
            if not kwargs:
                return None
            try:
                return IntervalTrigger(**kwargs)
            except Exception as exc:  # noqa: BLE001
                log_error("IntervalTrigger 构建失败", module="scheduler", error=str(exc))
                return None

        if trigger_type == "date":
            run_date = data.get("run_date")
            if not run_date:
                return None
            dt = None
            try:
                dt = time_utils.to_utc(str(run_date))
            except Exception:  # noqa: BLE001
                dt = None
            if dt is None:
                return None
            try:
                return DateTrigger(run_date=dt)
            except Exception as exc:  # noqa: BLE001
                log_error("DateTrigger 构建失败", module="scheduler", error=str(exc))
                return None

        return None
