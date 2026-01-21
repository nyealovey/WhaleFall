"""TaskRun 写入服务.

职责:
- 作为任务侧接入 TaskRun/TaskRunItem 的统一写入门面
- 不负责创建 app context；由 tasks/action service 保证
- 写入边界的 commit/rollback 由调用方控制
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from app import db
from app.core.exceptions import NotFoundError
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.utils.time_utils import time_utils


@dataclass(frozen=True, slots=True)
class TaskRunItemInit:
    """初始化 TaskRunItem 的输入结构."""

    item_type: str
    item_key: str
    item_name: str | None = None
    instance_id: int | None = None


class TaskRunsWriteService:
    """TaskRun 写入服务."""

    @staticmethod
    def _ensure_json_serializable(value: object) -> object:
        """将常见对象转换为可 JSON 序列化的结构(用于写入 JSON/JSONB 字段)."""
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Mapping):
            return {str(key): TaskRunsWriteService._ensure_json_serializable(val) for key, val in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [TaskRunsWriteService._ensure_json_serializable(item) for item in value]
        return value

    @staticmethod
    def _get_run_or_error(run_id: str) -> TaskRun:
        run = TaskRun.query.filter_by(run_id=run_id).first()
        if not run:
            raise NotFoundError("任务运行不存在")
        return run

    def start_run(
        self,
        *,
        task_key: str,
        task_name: str,
        task_category: str,
        trigger_source: str,
        created_by: int | None = None,
        summary_json: dict[str, Any] | None = None,
        result_url: str | None = None,
    ) -> str:
        """创建 TaskRun 并返回 run_id(由调用方控制 commit)."""
        run_id = str(uuid4())
        # SQLAlchemy Model __init__ signature isn't type-aware; assign fields explicitly for pyright.
        run = TaskRun()
        run.run_id = run_id
        run.task_key = task_key
        run.task_name = task_name
        run.task_category = task_category
        run.trigger_source = trigger_source
        run.status = "running"
        run.started_at = time_utils.now()
        run.created_by = created_by
        run.summary_json = None if summary_json is None else self._ensure_json_serializable(summary_json)
        run.result_url = result_url
        run.progress_total = 0
        run.progress_completed = 0
        run.progress_failed = 0
        db.session.add(run)
        return run_id

    def init_items(self, run_id: str, *, items: list[TaskRunItemInit]) -> None:
        """批量初始化 TaskRunItem，并更新 run.progress_total."""
        run = self._get_run_or_error(run_id)

        to_create: list[TaskRunItem] = []
        for item in items:
            row = TaskRunItem()
            row.run_id = run_id
            row.item_type = item.item_type
            row.item_key = item.item_key
            row.item_name = item.item_name
            row.instance_id = item.instance_id
            row.status = "pending"
            to_create.append(row)

        if to_create:
            db.session.add_all(to_create)

        run.progress_total = len(to_create)

    @staticmethod
    def _get_item_or_error(*, run_id: str, item_type: str, item_key: str) -> TaskRunItem:
        item = TaskRunItem.query.filter_by(run_id=run_id, item_type=item_type, item_key=item_key).first()
        if not item:
            raise NotFoundError("任务子项不存在")
        return item

    def start_item(self, run_id: str, *, item_type: str, item_key: str) -> None:
        """将指定子项标记为 running，并写入 started_at."""
        self._get_run_or_error(run_id)
        item = self._get_item_or_error(run_id=run_id, item_type=item_type, item_key=item_key)
        if item.status in {"completed", "failed", "cancelled"}:
            return
        item.status = "running"
        if item.started_at is None:
            item.started_at = time_utils.now()

    def complete_item(
        self,
        run_id: str,
        *,
        item_type: str,
        item_key: str,
        metrics_json: dict[str, Any] | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        """将指定子项标记为 completed，并写入完成时间与可选详情."""
        self._get_run_or_error(run_id)
        item = self._get_item_or_error(run_id=run_id, item_type=item_type, item_key=item_key)
        if item.status in {"failed", "cancelled"}:
            return
        item.status = "completed"
        item.completed_at = time_utils.now()
        if metrics_json is not None:
            item.metrics_json = self._ensure_json_serializable(metrics_json)
        if details_json is not None:
            item.details_json = self._ensure_json_serializable(details_json)

    def fail_item(
        self,
        run_id: str,
        *,
        item_type: str,
        item_key: str,
        error_message: str,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        """将指定子项标记为 failed，并写入错误信息与可选详情."""
        self._get_run_or_error(run_id)
        item = self._get_item_or_error(run_id=run_id, item_type=item_type, item_key=item_key)
        if item.status == "cancelled":
            return
        item.status = "failed"
        item.completed_at = time_utils.now()
        item.error_message = error_message
        if details_json is not None:
            item.details_json = self._ensure_json_serializable(details_json)

    def finalize_run(self, run_id: str) -> None:
        """汇总子项状态并更新 run 的进度与完成状态."""
        run = self._get_run_or_error(run_id)

        items = TaskRunItem.query.filter_by(run_id=run_id).all()
        total = len(items)
        completed = sum(1 for item in items if item.status == "completed")
        failed = sum(1 for item in items if item.status in {"failed", "cancelled"})

        run.progress_total = total
        run.progress_completed = completed
        run.progress_failed = failed

        if run.status not in {"cancelled", "failed"}:
            run.status = "failed" if failed > 0 else "completed"

        run.completed_at = time_utils.now()

    def cancel_run(self, run_id: str) -> bool:
        """取消任务运行(仅 running 可取消)，并将 pending/running 子项标记为 cancelled."""
        run = self._get_run_or_error(run_id)
        if run.status != "running":
            return False

        now = time_utils.now()
        run.status = "cancelled"
        run.completed_at = now

        items = TaskRunItem.query.filter_by(run_id=run_id).all()
        for item in items:
            if item.status in {"pending", "running"}:
                item.status = "cancelled"
                item.completed_at = now
        return True


# Backward-compatible alias for call sites
task_runs_write_service = TaskRunsWriteService()
