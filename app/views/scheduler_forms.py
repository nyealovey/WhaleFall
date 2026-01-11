"""定时任务表单视图."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Never

from flask import request
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import SQLAlchemyError

from app.errors import NotFoundError, SystemError, ValidationError
from app.forms.definitions.scheduler_job import SCHEDULER_JOB_FORM_DEFINITION
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.infra.route_safety import safe_route_call
from app.views.form_handlers.scheduler_job_form_handler import SchedulerJobFormHandler
from app.views.mixins.resource_forms import ResourceFormView

if TYPE_CHECKING:
    from app.services.scheduler.scheduler_job_write_service import SchedulerJobResource
else:
    SchedulerJobResource = Any

FORM_PROCESS_EXCEPTIONS: tuple[type[BaseException], ...] = (
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
)


class SchedulerJobFormView(ResourceFormView[SchedulerJobResource]):
    """统一处理定时任务编辑的视图.

    Attributes:
        form_definition: 定时任务表单定义配置.

    """

    form_definition = SCHEDULER_JOB_FORM_DEFINITION
    service_class = SchedulerJobFormHandler

    def get(self, *args: object, **kwargs: object) -> Never:
        """GET 请求处理(不支持).

        Raises:
            NotFoundError: 始终抛出,因为不支持此操作.

        Returns:
            Never returns; 总是抛出 NotFoundError.

        """
        del args, kwargs
        msg = "不支持的操作"
        raise NotFoundError(msg)

    def post(self, *args: object, **kwargs: object) -> Never:
        """POST 请求处理(不支持).

        Raises:
            NotFoundError: 始终抛出,因为不支持此操作.

        Returns:
            Never returns; 总是抛出 NotFoundError.

        """
        del args, kwargs
        msg = "不支持的操作"
        raise NotFoundError(msg)

    def put(self, job_id: str, **kwargs: object) -> ResponseReturnValue:
        """PUT 请求处理,更新定时任务.

        Args:
            job_id: 任务 ID.
            **kwargs: 额外的关键字参数.

        Returns:
            JSON 响应对象.

        Raises:
            NotFoundError: 当任务不存在时抛出.
            ValidationError: 当验证失败时抛出.
            SystemError: 当系统错误时抛出.

        """
        del kwargs
        resource = self._load_resource(job_id)
        payload = self._extract_payload(request)

        def _execute() -> ResponseReturnValue:
            self.service.upsert(payload, resource)
            return jsonify_unified_success(message=self.form_definition.success_message)

        try:
            return safe_route_call(
                _execute,
                module="scheduler",
                action="update_scheduler_job",
                public_error="任务更新失败",
                context={"job_id": job_id},
                expected_exceptions=FORM_PROCESS_EXCEPTIONS,
            )
        except (NotFoundError, ValidationError, SystemError):
            raise
        except FORM_PROCESS_EXCEPTIONS as exc:
            return jsonify_unified_error_message(message="任务更新失败", extra={"exception": str(exc)})

    def _load_resource(self, resource_id: str | int | None) -> SchedulerJobResource:
        """加载任务资源.

        Args:
            resource_id: 任务 ID.

        Returns:
            任务对象.

        """
        if resource_id is None:
            raise NotFoundError("定时任务不存在")
        resource = self.service.load(resource_id)
        if resource is None:
            raise NotFoundError("定时任务不存在")
        return resource
