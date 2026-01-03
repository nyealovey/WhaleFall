"""Scheduler namespace (Phase 4B 定时任务管理)."""

from __future__ import annotations

import threading
from typing import Any, ClassVar

from apscheduler.jobstores.base import JobLookupError
from flask import current_app, has_app_context, request
from flask_login import current_user
from flask_restx import Namespace, fields, marshal
from sqlalchemy.exc import SQLAlchemyError

import app.scheduler as scheduler_module
from app import create_app
from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.restx_models.scheduler import SCHEDULER_JOB_DETAIL_FIELDS, SCHEDULER_JOB_LIST_ITEM_FIELDS
from app.constants.scheduler_jobs import BUILTIN_TASK_IDS
from app.errors import ConflictError, NotFoundError
from app.services.scheduler.scheduler_job_write_service import SchedulerJobWriteService
from app.services.scheduler.scheduler_jobs_read_service import SchedulerJobsReadService
from app.utils.decorators import require_csrf
from app.utils.route_safety import log_with_context
from app.utils.structlog_config import log_info, log_warning

ns = Namespace("scheduler", description="定时任务管理")

ErrorEnvelope = get_error_envelope_model(ns)

SchedulerJobsListSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobsListSuccessEnvelope")
SchedulerJobDetailSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobDetailSuccessEnvelope")
SchedulerJobUpdateSuccessEnvelope = make_success_envelope_model(ns, "SchedulerJobUpdateSuccessEnvelope")

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

BACKGROUND_EXECUTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConflictError,
    NotFoundError,
    RuntimeError,
    ValueError,
    LookupError,
    SQLAlchemyError,
)
JOB_REMOVAL_EXCEPTIONS: tuple[type[BaseException], ...] = (JobLookupError, ValueError)


def _ensure_scheduler_running():
    scheduler = scheduler_module.get_scheduler()
    if scheduler is None or not getattr(scheduler, "running", False):
        log_warning("调度器未启动", module="scheduler")
        raise ConflictError("调度器未启动")
    return scheduler


@ns.route("/jobs")
class SchedulerJobsResource(BaseResource):
    """调度任务列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("scheduler.view")]

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
    @api_permission_required("scheduler.view")
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
    @api_permission_required("scheduler.manage")
    @require_csrf
    def put(self, job_id: str):
        """更新调度任务."""
        payload = request.get_json(silent=True) or {}

        def _execute():
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


@ns.route("/jobs/<string:job_id>/pause")
class SchedulerJobPauseResource(BaseResource):
    """调度任务暂停资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("scheduler.manage")]

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


@ns.route("/jobs/<string:job_id>/resume")
class SchedulerJobResumeResource(BaseResource):
    """调度任务恢复资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("scheduler.manage")]

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


@ns.route("/jobs/<string:job_id>/run")
class SchedulerJobRunResource(BaseResource):
    """调度任务立即执行资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("scheduler.manage")]

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
            scheduler = _ensure_scheduler_running()
            job = scheduler.get_job(job_id)
            if not job:
                raise NotFoundError("任务不存在")

            log_info("开始立即执行任务", module="scheduler", job_id=job_id, job_name=getattr(job, "name", None))

            created_by = getattr(current_user, "id", None)

            def _run_job_in_background(captured_created_by: int | None = created_by) -> None:
                base_app = current_app if has_app_context() else create_app(init_scheduler_on_start=False)
                try:
                    with base_app.app_context():
                        if job_id in BUILTIN_TASK_IDS:
                            manual_kwargs: dict[str, Any] = dict(getattr(job, "kwargs", {}) or {})
                            if job_id in ["sync_accounts", "calculate_database_size_aggregations"]:
                                manual_kwargs["manual_run"] = True
                                manual_kwargs["created_by"] = captured_created_by
                            job.func(*getattr(job, "args", ()), **manual_kwargs)
                        else:
                            job.func(*getattr(job, "args", ()), **(getattr(job, "kwargs", {}) or {}))

                    log_info(
                        "任务立即执行成功",
                        module="scheduler",
                        job_id=job_id,
                        job_name=getattr(job, "name", None),
                    )
                except BACKGROUND_EXECUTION_EXCEPTIONS as func_error:  # pragma: no cover - defensive log
                    log_with_context(
                        "error",
                        "任务函数执行失败",
                        module="scheduler",
                        action="run_job_background",
                        context={"job_id": job_id, "job_name": getattr(job, "name", None)},
                        extra={
                            "error_type": func_error.__class__.__name__,
                            "error_message": str(func_error),
                        },
                    )

            thread = threading.Thread(target=_run_job_in_background, name=f"{job_id}_manual", daemon=True)
            thread.start()
            return self.success(data={"manual_job_id": thread.name}, message="任务已提交后台执行")

        return self.safe_call(
            _execute,
            module="scheduler",
            action="run_job",
            public_error="执行任务失败",
            context={"job_id": job_id},
            expected_exceptions=(NotFoundError, ConflictError),
        )


@ns.route("/jobs/reload")
class SchedulerJobsReloadResource(BaseResource):
    """调度任务重新加载资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("scheduler.manage")]

    @ns.response(200, "OK", SchedulerJobsReloadSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(409, "Conflict", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self):
        """重新加载调度任务."""

        def _execute():
            scheduler = _ensure_scheduler_running()
            existing_jobs = scheduler.get_jobs()
            existing_job_ids = [job.id for job in existing_jobs]

            deleted_count = 0
            for job_id in existing_job_ids:
                try:
                    scheduler.remove_job(job_id)
                except JOB_REMOVAL_EXCEPTIONS as del_err:
                    log_with_context(
                        "error",
                        "重新加载-删除任务失败",
                        module="scheduler",
                        action="reload_jobs",
                        context={"job_id": job_id},
                        extra={
                            "error_type": del_err.__class__.__name__,
                            "error_message": str(del_err),
                        },
                    )
                else:
                    deleted_count += 1
                    log_info("重新加载-删除任务", module="scheduler", job_id=job_id)

            scheduler_module._reload_all_jobs()

            reloaded_jobs = scheduler.get_jobs()
            reloaded_job_ids = [job.id for job in reloaded_jobs]

            log_info(
                "任务重新加载完成",
                module="scheduler",
                deleted_count=deleted_count,
                reloaded_count=len(reloaded_jobs),
            )
            return self.success(
                data={
                    "deleted": existing_job_ids,
                    "reloaded": reloaded_job_ids,
                    "deleted_count": deleted_count,
                    "reloaded_count": len(reloaded_jobs),
                },
                message=f"已删除 {deleted_count} 个任务,重新加载 {len(reloaded_jobs)} 个任务",
            )

        return self.safe_call(
            _execute,
            module="scheduler",
            action="reload_jobs",
            public_error="重新加载任务失败",
            context={"endpoint": "reload_jobs"},
            expected_exceptions=(ConflictError,),
        )
