"""定时任务表单服务.

提供内置定时任务触发器的编辑功能,支持 Cron、Interval 和 Date 三种触发器类型.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast
from zoneinfo import ZoneInfo

try:
    from apscheduler.exceptions import APSchedulerError  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover - 兼容 APScheduler 4.x
    try:
        from apscheduler.exc import SchedulerError as APSchedulerError  # type: ignore[reportMissingImports]
    except ModuleNotFoundError:
        APSchedulerError = Exception  # type: ignore[misc]

from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import NotFoundError, SystemError, ValidationError
from app.scheduler import get_scheduler
from app.services.form_service.resource_service import BaseResourceService, ServiceResult
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

try:
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.triggers.interval import IntervalTrigger
except ModuleNotFoundError as trigger_import_error:  # pragma: no cover - 兼容无 APScheduler 环境

    missing_trigger_error = trigger_import_error

    class _MissingTrigger:
        """兜底触发器占位类型,用于提示缺失 APScheduler 依赖."""

        def __init__(self, *_: object, **__: object) -> None:
            msg = "未安装 APScheduler 触发器依赖,无法构建定时任务触发器"
            raise ModuleNotFoundError(msg) from missing_trigger_error

    CronTrigger = IntervalTrigger = DateTrigger = _MissingTrigger  # type: ignore[assignment]

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
        """初始化资源 id,兼容 apscheduler Job 接口."""
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

    def validate(
        self, data: MutablePayloadDict, *, resource: SchedulerJobResource | None,
    ) -> ServiceResult[MutablePayloadDict]:
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

        trigger_type = as_str(data.get("trigger_type"), default="").strip()
        if not trigger_type:
            return ServiceResult.fail("缺少触发器类型配置", message_key="VALIDATION_ERROR")

        trigger = self._build_trigger(trigger_type, data)
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

    def upsert(
        self, payload: PayloadMapping, resource: SchedulerJobResource | None = None,
    ) -> ServiceResult[SchedulerJobResource]:
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
            return ServiceResult.fail(
                validation.message or "验证失败", message_key=validation.message_key, extra=validation.extra,
            )

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

    def _build_trigger(
        self,
        trigger_type: str,
        data: PayloadMapping,
    ) -> TriggerUnion | None:
        """根据触发器类型分发到具体构建函数."""
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
        """基于 cron 表达式或分段字段构建触发器."""
        cron_kwargs = self._collect_cron_fields(data)
        if not cron_kwargs:
            return None
        try:
            return CronTrigger(timezone=ZoneInfo("Asia/Shanghai"), **cron_kwargs)
        except (ValueError, TypeError) as exc:
            log_error("CronTrigger 构建失败", module="scheduler", error=str(exc))
            return None

    def _collect_cron_fields(self, data: PayloadMapping) -> dict[str, str]:
        """收集 cron 字段,支持整行表达式与分段字段混合覆盖."""
        base_fields = self._extract_cron_base_fields(data)
        parts = self._split_cron_expression(data)
        merged_fields = self._apply_expression_overrides(parts, base_fields)
        return self._build_cron_kwargs(merged_fields)

    def _extract_cron_base_fields(self, data: PayloadMapping) -> dict[str, str | None]:
        """从表单字段提取 cron 各字段."""
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
        """将 cron 表达式拆分为列表."""
        expr = as_str(data.get("cron_expression"), default="").strip()
        return expr.split() if expr else []

    def _apply_expression_overrides(
        self,
        parts: list[str],
        base_fields: dict[str, str | None],
    ) -> dict[str, str | None]:
        """用表达式分段覆盖缺失字段."""
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
        """过滤掉空值生成 CronTrigger 所需参数."""
        return {key: value for key, value in fields.items() if value is not None}

    @staticmethod
    def _pick(data: PayloadMapping, *keys: str) -> str | None:
        """按顺序选择第一个有值的字段."""
        for key in keys:
            candidate = as_optional_str(data.get(key))
            if candidate:
                return candidate
        return None

    @staticmethod
    def _merge_parts(parts: list[str], picked: list[str | None]) -> list[str]:
        """用表达式分段填充缺失字段."""
        return [
            pick_value or part
            for pick_value, part in zip(
                picked,
                parts,
                strict=False,
            )
        ]

    def _build_interval_trigger(self, data: PayloadMapping) -> TriggerUnion | None:
        """基于 interval 字段构建触发器."""
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
        """基于单次运行时间构建触发器."""
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
