"""TaskRun Center Repository.

职责:
- 仅负责 Query 组装与数据库读取
- 不做序列化、不返回 Response、不 commit
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import NotFoundError
from app.core.types.listing import PaginatedResult
from app.core.types.task_runs import TaskRunsListFilters
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem


class TaskRunsRepository:
    """任务运行查询 Repository."""

    def list_runs(self, filters: TaskRunsListFilters) -> PaginatedResult[TaskRun]:
        started_at_column = cast("ColumnElement[Any]", TaskRun.started_at)
        completed_at_column = cast("ColumnElement[Any]", TaskRun.completed_at)
        status_column = cast(ColumnElement[str], TaskRun.status)

        sortable_fields = {
            "started_at": started_at_column,
            "completed_at": completed_at_column,
            "status": status_column,
        }
        sort_column = sortable_fields.get(filters.sort_field, started_at_column)
        ordering = sort_column.asc() if filters.sort_order == "asc" else sort_column.desc()

        query = TaskRun.query
        if filters.task_key:
            query = query.filter(TaskRun.task_key == filters.task_key)
        if filters.task_category:
            query = query.filter(TaskRun.task_category == filters.task_category)
        if filters.trigger_source:
            query = query.filter(TaskRun.trigger_source == filters.trigger_source)
        if filters.status:
            query = query.filter(TaskRun.status == filters.status)

        query = query.order_by(ordering, TaskRun.id.desc())
        pagination = cast(Any, query).paginate(page=filters.page, per_page=filters.limit, error_out=False)
        return PaginatedResult(
            items=list(pagination.items),
            total=pagination.total,
            page=pagination.page,
            pages=pagination.pages,
            limit=pagination.per_page,
        )

    @staticmethod
    def get_run(run_id: str) -> TaskRun:
        run = TaskRun.query.filter_by(run_id=run_id).first()
        if not run:
            raise NotFoundError("任务运行不存在")
        return run

    @staticmethod
    def list_run_items(run_id: str) -> list[TaskRunItem]:
        return TaskRunItem.query.filter_by(run_id=run_id).order_by(TaskRunItem.id.asc()).all()
