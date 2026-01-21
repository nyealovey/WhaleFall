"""TaskRun Center read APIs Service.

职责:
- 组织 repository 调用并输出稳定 DTO
- 不做 Query 细节、不做序列化/Response、不 commit
"""

from __future__ import annotations

from app.core.types.listing import PaginatedResult
from app.core.types.task_runs import (
    TaskRunDetailResult,
    TaskRunErrorLogsResult,
    TaskRunItemItem,
    TaskRunListItem,
    TaskRunsListFilters,
)
from app.models.task_run import TaskRun
from app.models.task_run_item import TaskRunItem
from app.repositories.task_runs_repository import TaskRunsRepository


class TaskRunsReadService:
    """任务运行读取服务."""

    def __init__(self, repository: TaskRunsRepository | None = None) -> None:
        """初始化服务并注入 repository."""
        self._repository = repository or TaskRunsRepository()

    def list_runs(self, filters: TaskRunsListFilters) -> PaginatedResult[TaskRunListItem]:
        """分页列出任务运行记录."""
        page_result = self._repository.list_runs(filters)
        items = [self._to_run_item(run) for run in page_result.items]
        return PaginatedResult(
            items=items,
            total=page_result.total,
            page=page_result.page,
            pages=page_result.pages,
            limit=page_result.limit,
        )

    def get_run_detail(self, run_id: str) -> TaskRunDetailResult:
        """获取任务运行详情(含子项列表)."""
        run = self._repository.get_run(run_id)
        items = self._repository.list_run_items(run_id)
        return TaskRunDetailResult(
            run=self._to_run_item(run),
            items=[self._to_item_item(item) for item in items],
        )

    def get_run_error_logs(self, run_id: str) -> TaskRunErrorLogsResult:
        """获取任务运行失败子项(错误日志列表)."""
        run = self._repository.get_run(run_id)
        items = self._repository.list_run_items(run_id)
        failed = [item for item in items if item.status == "failed"]
        return TaskRunErrorLogsResult(
            run=self._to_run_item(run),
            items=[self._to_item_item(item) for item in failed],
            error_count=len(failed),
        )

    @staticmethod
    def _to_run_item(run: TaskRun) -> TaskRunListItem:
        return TaskRunListItem(
            id=(0 if run.id is None else int(run.id)),
            run_id=run.run_id,
            task_key=run.task_key,
            task_name=run.task_name,
            task_category=run.task_category,
            trigger_source=run.trigger_source,
            status=run.status,
            started_at=(run.started_at.isoformat() if run.started_at else None),
            completed_at=(run.completed_at.isoformat() if run.completed_at else None),
            progress_total=(0 if run.progress_total is None else int(run.progress_total)),
            progress_completed=(0 if run.progress_completed is None else int(run.progress_completed)),
            progress_failed=(0 if run.progress_failed is None else int(run.progress_failed)),
            created_by=run.created_by,
            summary_json=run.summary_json,
            result_url=run.result_url,
            error_message=run.error_message,
            created_at=(run.created_at.isoformat() if run.created_at else None),
            updated_at=(run.updated_at.isoformat() if run.updated_at else None),
        )

    @staticmethod
    def _to_item_item(item: TaskRunItem) -> TaskRunItemItem:
        return TaskRunItemItem(
            id=(0 if item.id is None else int(item.id)),
            run_id=item.run_id,
            item_type=item.item_type,
            item_key=item.item_key,
            item_name=item.item_name,
            instance_id=item.instance_id,
            status=item.status,
            started_at=(item.started_at.isoformat() if item.started_at else None),
            completed_at=(item.completed_at.isoformat() if item.completed_at else None),
            metrics_json=item.metrics_json,
            details_json=item.details_json,
            error_message=item.error_message,
            created_at=(item.created_at.isoformat() if item.created_at else None),
            updated_at=(item.updated_at.isoformat() if item.updated_at else None),
        )
