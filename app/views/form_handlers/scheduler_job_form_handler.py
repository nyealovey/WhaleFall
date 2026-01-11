"""定时任务表单处理器(View layer)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.scheduler.scheduler_job_write_service import SchedulerJobWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload

if TYPE_CHECKING:
    from app.services.scheduler.scheduler_job_write_service import SchedulerJobResource


class SchedulerJobFormHandler:
    """定时任务表单处理器."""

    def __init__(self, service: SchedulerJobWriteService | None = None) -> None:
        self._service = service or SchedulerJobWriteService()

    def load(self, resource_id: ResourceIdentifier) -> "SchedulerJobResource":
        """加载定时任务资源."""
        return self._service.load(resource_id)

    def upsert(self, payload: ResourcePayload, resource: "SchedulerJobResource | None" = None) -> "SchedulerJobResource":
        """创建或更新定时任务."""
        return self._service.upsert(payload, resource)

    def build_context(self, *, resource: "SchedulerJobResource | None") -> ResourceContext:
        """构造表单渲染上下文."""
        del resource
        return {}

