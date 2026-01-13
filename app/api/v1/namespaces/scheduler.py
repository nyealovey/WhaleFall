"""Scheduler namespace (Phase 4B 定时任务管理)."""

from __future__ import annotations

from typing import ClassVar

from flask import request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.restx_models.scheduler import SCHEDULER_JOB_DETAIL_FIELDS, SCHEDULER_JOB_LIST_ITEM_FIELDS
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.services.scheduler.scheduler_actions_service import SchedulerActionsService
from app.services.scheduler.scheduler_job_write_service import SchedulerJobWriteService
from app.services.scheduler.scheduler_jobs_read_service import SchedulerJobsReadService
from app.utils.decorators import require_csrf
from app.utils.structlog_config import log_info

ns = Namespace("scheduler", description="定时任务管理")

ErrorEnvelope = get_error_envelope_model(ns)

SchedulerJobsListSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobsListSuccessEnvelope")
SchedulerJobDetailSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobDetailSuccessEnvelope")
SchedulerJobUpdateSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobUpdateSuccessEnvelope")

SchedulerJobUpdatePayload = ns.model(
    "SchedulerJobUpdatePayload",
    {
        "trigger_type": fields.String(required=True, description="触发器类型", example="cron"),
        "cron_expression": fields.String(required=True, description="cron 表达式", example="*/5 * * * *"),
    },
)

SchedulerJobRunData = ns.model(
    "SchedulerJobRunData",
    {
        "manual_job_id": fields.String(required=True),
    },
)
SchedulerJobRunSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobRunSuccessEnvelope", SchedulerJobRunData)

SchedulerJobsReloadData = ns.model(
    "SchedulerJobsReloadData",
    {
        "deleted": fields.List(fields.String, required=True),
        "reloaded": fields.List(fields.String, required=True),
        "deleted_count": fields.Integer(required=True),
        "reloaded_count": fields.Integer(required=True),
    },
)
SchedulerJobsReloadSuccessEnvelope = make_success_envelope_model(
    ns,
    "SchedulerJobsReloadSuccessEnvelope",
    SchedulerJobsReloadData,
)


def _ensure_scheduler_running():
    return SchedulerActionsService.ensure_scheduler_running()


@ns.route("/jobs")
class SchedulerJobsResource(BaseResource):
    """调度任务列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", SchedulerJobsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self):
        """获取调度任务列表."""

        def _execute():
            jobs = SchedulerJobsReadService().list_jobs()
            payload = marshal(jobs, SCHEDULER_JOB_LIST_ITEM_FIELDS)
            log_info("获取任务列表成功", module="scheduler", job_count=len(payload))
            return self.success(data=payload, message="任务列表获取成功")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="get_jobs",
            public_error="获取任务列表失败",
            context={"endpoint": "jobs"},
            expected_exceptions=(ConflictError,),
        )


@ns.route("/jobs/<string:job_id>")
class SchedulerJobDetailResource(BaseResource):
    """调度任务详情资源."""

    method_decorators: ClassVar[list] = [api_login_required]

    @ns.response(200, "OK", SchedulerJobDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("view")
    def get(self, job_id: str):
        """获取调度任务详情."""

        def _execute():
            job = SchedulerJobsReadService().get_job(job_id)
            payload = marshal(job, SCHEDULER_JOB_DETAIL_FIELDS)
            log_info("获取任务详情成功", module="scheduler", job_id=job_id)
            return self.success(data=payload, message="任务详情获取成功")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="get_job",
            public_error="获取任务详情失败",
            context={"job_id": job_id},
            expected_exceptions=(NotFoundError, ConflictError),
        )

    @ns.response(200, "OK", SchedulerJobUpdateSuccessEnvelope)
    @ns.response(400, "Bad Request", ErrorEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @api_permission_required("admin")
    @ns.expect(SchedulerJobUpdatePayload, validate=False)
    @require_csrf
    def put(self, job_id: str):
        """更新调度任务."""

        def _execute():
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict) or not payload:
                raise ValidationError("请求体必须是非空 JSON object", message_key="VALIDATION_ERROR")
            service = SchedulerJobWriteService()
            resource = service.load(job_id)
            service.upsert(payload, resource)
            return self.success(message="任务更新成功")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="update_scheduler_job",
            public_error="任务更新失败",
            context={"job_id": job_id},
        )


@ns.route("/jobs/<string:job_id>/actions/pause")
class SchedulerJobPauseResource(BaseResource):
    """调度任务暂停资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", make_success_envelope_model(ns, "SchedulerJobPauseSuccessEnvelope"))
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, job_id: str):
        """暂停调度任务."""

        def _execute():
            scheduler = _ensure_scheduler_running()
            scheduler.pause_job(job_id)
            log_info("任务暂停成功", module="scheduler", job_id=job_id)
            return self.success(message="任务暂停成功")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="pause_job",
            public_error="暂停任务失败",
            context={"job_id": job_id},
            expected_exceptions=(ConflictError,),
        )


@ns.route("/jobs/<string:job_id>/actions/resume")
class SchedulerJobResumeResource(BaseResource):
    """调度任务恢复资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", make_success_envelope_model(ns, "SchedulerJobResumeSuccessEnvelope"))
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, job_id: str):
        """恢复调度任务."""

        def _execute():
            scheduler = _ensure_scheduler_running()
            scheduler.resume_job(job_id)
            log_info("任务恢复成功", module="scheduler", job_id=job_id)
            return self.success(message="任务恢复成功")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="resume_job",
            public_error="恢复任务失败",
            context={"job_id": job_id},
            expected_exceptions=(ConflictError,),
        )


@ns.route("/jobs/<string:job_id>/actions/run")
class SchedulerJobRunResource(BaseResource):
    """调度任务立即执行资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", SchedulerJobRunSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, job_id: str):
        """立即执行调度任务."""

        def _execute():
            created_by = getattr(current_user, "id", None)
            manual_job_id = SchedulerActionsService().run_job_in_background(job_id=job_id, created_by=created_by)
            return self.success(data={"manual_job_id": manual_job_id}, message="任务已提交后台执行")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="run_job",
            public_error="执行任务失败",
            context={"job_id": job_id},
            expected_exceptions=(NotFoundError, ConflictError),
        )


@ns.route("/jobs/actions/reload")
class SchedulerJobsReloadResource(BaseResource):
    """调度任务重新加载资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", SchedulerJobsReloadSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """重新加载调度任务."""

        def _execute():
            result = SchedulerActionsService().reload_jobs()
            return self.success(
                data={
                    "deleted": result.deleted,
                    "reloaded": result.reloaded,
                    "deleted_count": result.deleted_count,
                    "reloaded_count": result.reloaded_count,
                },
                message=f"已删除 {result.deleted_count} 个任务,重新加载 {result.reloaded_count} 个任务",
            )

        return self.safe_call(
            _execute,
            module="scheduler",
            action="reload_jobs",
            public_error="重新加载任务失败",
            context={"endpoint": "reload_jobs"},
            expected_exceptions=(ConflictError,),
        )
