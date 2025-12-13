"""定时任务表单视图."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Never

from flask import Response, request
from sqlalchemy.exc import SQLAlchemyError

from app.errors import NotFoundError, SystemError, ValidationError
from app.forms.definitions.scheduler_job import SCHEDULER_JOB_FORM_DEFINITION
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.views.mixins.resource_forms import ResourceFormView

if TYPE_CHECKING:
    from app.services.form_service.scheduler_job_service import SchedulerJobResource
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

    def put(self, job_id: str, **kwargs: object) -> Response:
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
        try:
            resource = self._load_resource(job_id)
            payload = self._extract_payload(request)
            result = self.service.upsert(payload, resource)
            if result.success:
                return jsonify_unified_success(message=self.form_definition.success_message)
            return jsonify_unified_error_message(
                message=result.message or "任务更新失败",
                message_key=result.message_key,
                extra=result.extra,
            )
        except (NotFoundError, ValidationError, SystemError):
            raise
        except FORM_PROCESS_EXCEPTIONS as exc:
            return jsonify_unified_error_message(message="任务更新失败", extra={"exception": str(exc)})

    def _load_resource(self, job_id: str) -> SchedulerJobResource:
        """加载任务资源.

        Args:
            job_id: 任务 ID.

        Returns:
            任务对象.

        """
        return self.service.load(job_id)
