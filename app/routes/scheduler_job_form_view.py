"""
定时任务表单视图
"""

from flask import Response, jsonify, request

from app.errors import NotFoundError, SystemError, ValidationError
from app.forms.definitions.scheduler_job import SCHEDULER_JOB_FORM_DEFINITION
from app.routes.mixins.resource_form_view import ResourceFormView
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success


class SchedulerJobFormView(ResourceFormView):
    form_definition = SCHEDULER_JOB_FORM_DEFINITION

    def get(self, *args, **kwargs):
        raise NotFoundError("不支持的操作")

    def post(self, *args, **kwargs):
        raise NotFoundError("不支持的操作")

    def put(self, job_id: str, **kwargs) -> Response:
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
        except Exception as exc:  # noqa: BLE001
            return jsonify_unified_error_message(message="任务更新失败", extra={"exception": str(exc)})

    def _load_resource(self, job_id):
        return self.service.load(job_id)
