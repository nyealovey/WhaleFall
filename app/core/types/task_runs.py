"""TaskRun Center 相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class TaskRunsListFilters:
    """任务运行列表查询参数."""

    task_key: str
    task_category: str
    trigger_source: str
    status: str
    page: int
    limit: int
    sort_field: str
    sort_order: str


@dataclass(slots=True)
class TaskRunListItem:
    """任务运行列表条目."""

    id: int
    run_id: str
    task_key: str
    task_name: str
    task_category: str
    trigger_source: str
    status: str
    started_at: str | None
    completed_at: str | None
    progress_total: int
    progress_completed: int
    progress_failed: int
    created_by: int | None
    summary_json: Any
    result_url: str | None
    error_message: str | None
    created_at: str | None
    updated_at: str | None


@dataclass(slots=True)
class TaskRunItemItem:
    """任务运行子项条目."""

    id: int
    run_id: str
    item_type: str
    item_key: str
    item_name: str | None
    instance_id: int | None
    status: str
    started_at: str | None
    completed_at: str | None
    metrics_json: Any
    details_json: Any
    error_message: str | None
    created_at: str | None
    updated_at: str | None


@dataclass(slots=True)
class TaskRunDetailResult:
    """任务运行详情结果."""

    run: TaskRunListItem
    items: list[TaskRunItemItem]


@dataclass(slots=True)
class TaskRunErrorLogsResult:
    """任务运行错误日志结果."""

    run: TaskRunListItem
    items: list[TaskRunItemItem]
    error_count: int
