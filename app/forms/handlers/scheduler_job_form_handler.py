"""定时任务表单处理器."""

from __future__ import annotations

from app.services.scheduler.scheduler_job_write_service import SchedulerJobResource, SchedulerJobWriteService
from app.types import ResourceContext, ResourceIdentifier, ResourcePayload


class SchedulerJobFormHandler:
    """定时任务表单处理器."""

    def __init__(self, service: SchedulerJobWriteService | None = None) -> None:
        self._service = service or SchedulerJobWriteService()

    def load(self, resource_id: ResourceIdentifier) -> SchedulerJobResource:
        return self._service.load(resource_id)

    def upsert(
        self,
        payload: ResourcePayload,
        resource: SchedulerJobResource | None = None,
    ) -> SchedulerJobResource:
        return self._service.upsert(payload, resource)

    def build_context(self, *, resource: SchedulerJobResource | None) -> ResourceContext:
        del resource
        return {}
