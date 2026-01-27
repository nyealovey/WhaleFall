"""Capacity current aggregation actions service.

将“容量统计 - 统计当前周期”动作的编排逻辑下沉到 service 层：
- 校验参数
- 创建 TaskRun 并返回 run_id
- 启动后台线程执行 `capacity_aggregate_current`
"""

from __future__ import annotations

import importlib
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import SystemError, ValidationError
from app.infra.route_safety import log_with_context
from app.schemas.task_run_summary import TaskRunSummaryFactory
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

_ALLOWED_SCOPES = {"instance", "database", "all"}

BACKGROUND_EXCEPTIONS: tuple[type[Exception], ...] = (
    ValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


@dataclass(frozen=True, slots=True)
class CapacityCurrentAggregationPreparedRun:
    """后台聚合准备结果(已创建 TaskRun,尚未启动线程)."""

    run_id: str
    scope: str


@dataclass(frozen=True, slots=True)
class CapacityCurrentAggregationLaunchResult:
    """后台聚合启动结果."""

    run_id: str
    scope: str
    thread_name: str


def _validate_scope(scope: str) -> str:
    cleaned = (scope or "all").strip().lower()
    if cleaned not in _ALLOWED_SCOPES:
        raise ValidationError("scope 参数仅支持 instance、database 或 all")
    return cleaned


def _resolve_default_task() -> Callable[..., Any]:
    """惰性加载默认任务函数,避免导入期循环依赖."""
    module = importlib.import_module("app.tasks.capacity_current_aggregation_tasks")
    return cast("Callable[..., Any]", module.capacity_aggregate_current)


def _launch_background_aggregation(
    *,
    created_by: int | None,
    run_id: str,
    scope: str,
    task: Callable[..., Any],
) -> threading.Thread:
    def _run_task(captured_created_by: int | None, captured_run_id: str, captured_scope: str) -> None:
        try:
            task(
                scope=captured_scope,
                created_by=captured_created_by,
                run_id=captured_run_id,
            )
        except BACKGROUND_EXCEPTIONS as exc:
            log_with_context(
                "error",
                "后台统计当前周期失败",
                module="capacity_aggregations",
                action="capacity_aggregate_current_background",
                context={
                    "created_by": captured_created_by,
                    "run_id": captured_run_id,
                    "scope": captured_scope,
                },
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
                include_actor=False,
            )

    thread = threading.Thread(
        target=_run_task,
        args=(created_by, run_id, scope),
        name="capacity_aggregate_current_manual",
        daemon=True,
    )
    thread.start()
    return thread


class CapacityCurrentAggregationActionsService:
    """当前周期聚合动作编排服务."""

    def __init__(self, *, task: Callable[..., Any] | None = None) -> None:
        """初始化服务并允许注入 task(便于测试/替换执行入口)."""
        self._task = task or _resolve_default_task()

    def prepare_background_aggregation(
        self,
        *,
        created_by: int | None,
        scope: str,
        result_url: str,
    ) -> CapacityCurrentAggregationPreparedRun:
        """创建 TaskRun 并返回 run_id(不启动线程)."""
        normalized_scope = _validate_scope(scope)
        run_id = TaskRunsWriteService().start_run(
            task_key="capacity_aggregate_current",
            task_name="容量统计(当前周期)",
            task_category="aggregation",
            trigger_source="manual",
            created_by=created_by,
            summary_json=TaskRunSummaryFactory.base(
                task_key="capacity_aggregate_current",
                inputs={"scope": normalized_scope},
            ),
            result_url=result_url,
        )
        return CapacityCurrentAggregationPreparedRun(run_id=run_id, scope=normalized_scope)

    def launch_background_aggregation(
        self,
        *,
        created_by: int | None,
        prepared: CapacityCurrentAggregationPreparedRun,
    ) -> CapacityCurrentAggregationLaunchResult:
        """启动后台线程执行当前周期聚合."""
        thread = _launch_background_aggregation(
            created_by=created_by,
            run_id=prepared.run_id,
            scope=prepared.scope,
            task=self._task,
        )
        return CapacityCurrentAggregationLaunchResult(
            run_id=prepared.run_id,
            scope=prepared.scope,
            thread_name=thread.name,
        )
