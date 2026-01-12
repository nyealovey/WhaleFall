"""调度器相关类型定义."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SchedulerJobListItem:
    """任务列表项."""

    id: str
    name: str
    description: str
    next_run_time: str | None
    last_run_time: str | None
    trigger_type: str
    trigger_args: dict[str, str]
    state: str
    is_builtin: bool
    func: str
    args: tuple[object, ...]
    kwargs: dict[str, object] | None


@dataclass(slots=True)
class SchedulerJobDetail:
    """任务详情."""

    id: str
    name: str
    next_run_time: str | None
    trigger: str
    func: str
    args: tuple[object, ...]
    kwargs: dict[str, object] | None
    misfire_grace_time: int | None
    max_instances: int | None
    coalesce: bool | None
