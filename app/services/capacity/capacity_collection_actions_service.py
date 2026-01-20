"""Capacity collection actions service.

将“数据库台账 - 同步所有数据库”动作的编排逻辑下沉到 service 层：
- 校验活跃实例
- 创建 TaskRun 并返回 run_id
- 启动后台线程执行 `collect_database_sizes`
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
from app.repositories.instances_repository import InstancesRepository
from app.services.task_runs.task_runs_write_service import TaskRunsWriteService

BACKGROUND_SYNC_EXCEPTIONS: tuple[type[Exception], ...] = (
    ValidationError,
    SystemError,
    SQLAlchemyError,
    RuntimeError,
)


@dataclass(frozen=True, slots=True)
class CapacityCollectionBackgroundPreparedRun:
    """后台容量同步准备结果(已创建 TaskRun,尚未启动线程)."""

    run_id: str
    active_instance_count: int


@dataclass(frozen=True, slots=True)
class CapacityCollectionBackgroundLaunchResult:
    """后台容量同步启动结果."""

    run_id: str
    active_instance_count: int
    thread_name: str


def _resolve_default_task() -> Callable[..., Any]:
    """惰性加载默认任务函数,避免导入期循环依赖."""
    module = importlib.import_module("app.tasks.capacity_collection_tasks")
    return cast("Callable[..., Any]", module.collect_database_sizes)


def _launch_background_collection(
    *,
    created_by: int | None,
    run_id: str,
    task: Callable[..., Any],
) -> threading.Thread:
    def _run_task(captured_created_by: int | None, captured_run_id: str) -> None:
        try:
            task(manual_run=True, created_by=captured_created_by, run_id=captured_run_id)
        except BACKGROUND_SYNC_EXCEPTIONS as exc:  # pragma: no cover
            log_with_context(
                "error",
                "后台容量同步失败",
                module="capacity_sync",
                action="collect_database_sizes_background",
                context={
                    "created_by": captured_created_by,
                    "run_id": captured_run_id,
                },
                extra={
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                },
                include_actor=False,
            )

    thread = threading.Thread(
        target=_run_task,
        args=(created_by, run_id),
        name="collect_database_sizes_manual",
        daemon=True,
    )
    thread.start()
    return thread


class CapacityCollectionActionsService:
    """容量同步动作编排服务."""

    def __init__(
        self,
        *,
        task: Callable[..., Any] | None = None,
    ) -> None:
        self._task = task or _resolve_default_task()

    @staticmethod
    def _ensure_active_instances() -> int:
        active_count = InstancesRepository.count_active_instances()
        if active_count == 0:
            raise ValidationError("没有找到活跃的数据库实例")
        return int(active_count)

    def prepare_background_collection(self, *, created_by: int | None) -> CapacityCollectionBackgroundPreparedRun:
        """创建 TaskRun 并返回 run_id(不启动线程)."""
        active_instance_count = self._ensure_active_instances()
        run_id = TaskRunsWriteService().start_run(
            task_key="collect_database_sizes",
            task_name="容量同步",
            task_category="capacity",
            trigger_source="manual",
            created_by=created_by,
            summary_json=None,
            result_url="/databases/ledgers",
        )
        return CapacityCollectionBackgroundPreparedRun(
            run_id=run_id,
            active_instance_count=active_instance_count,
        )

    def launch_background_collection(
        self,
        *,
        created_by: int | None,
        prepared: CapacityCollectionBackgroundPreparedRun,
    ) -> CapacityCollectionBackgroundLaunchResult:
        """启动后台线程执行容量同步."""
        thread = _launch_background_collection(
            created_by=created_by,
            run_id=prepared.run_id,
            task=self._task,
        )
        return CapacityCollectionBackgroundLaunchResult(
            run_id=prepared.run_id,
            active_instance_count=prepared.active_instance_count,
            thread_name=thread.name,
        )
