"""Task runs namespace (TaskRun Center).

提供任务运行中心的查询与取消能力。

Note:
- 本 namespace 是对外 JSON API 层的路由封装；业务编排与 DB 访问下沉到 services/repositories.

"""

from __future__ import annotations

from dataclasses import asdict
from typing import ClassVar

from flask_restx import Namespace, fields

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.core.exceptions import NotFoundError
from app.core.types.task_runs import TaskRunsListFilters
from app.schemas.task_runs_query import TaskRunsListFiltersQuery
from app.schemas.validation import validate_or_raise
from app.services.task_runs.task_runs_read_service import TaskRunsReadService
from app.services.task_runs.task_runs_write_service import task_runs_write_service
from app.utils.decorators import require_csrf

ns = Namespace("task_runs", description="任务运行中心")

ErrorEnvelope = get_error_envelope_model(ns)


TaskRunsListData = ns.model(
    "TaskRunsListData",
    {
        "items": fields.Raw(required=True),
        "total": fields.Integer(required=True),
        "page": fields.Integer(required=True),
        "pages": fields.Integer(required=True),
    },
)
TaskRunsListSuccessEnvelope = make_success_envelope_model(ns, "TaskRunsListSuccessEnvelope", TaskRunsListData)

TaskRunDetailSuccessEnvelope = make_success_envelope_model(ns, "TaskRunDetailSuccessEnvelope")
TaskRunErrorLogsSuccessEnvelope = make_success_envelope_model(ns, "TaskRunErrorLogsSuccessEnvelope")
TaskRunCancelSuccessEnvelope = make_success_envelope_model(ns, "TaskRunCancelSuccessEnvelope")

_task_runs_list_query_parser = new_parser()
_task_runs_list_query_parser.add_argument("task_key", type=str, default="", location="args")
_task_runs_list_query_parser.add_argument("task_category", type=str, default="", location="args")
_task_runs_list_query_parser.add_argument("trigger_source", type=str, default="", location="args")
_task_runs_list_query_parser.add_argument("status", type=str, default="", location="args")
_task_runs_list_query_parser.add_argument("page", type=int, default=1, location="args")
_task_runs_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_task_runs_list_query_parser.add_argument("sort", type=str, default="started_at", location="args")
_task_runs_list_query_parser.add_argument("order", type=str, default="desc", location="args")


@ns.route("")
class TaskRunsListResource(BaseResource):
    """任务运行列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TaskRunsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_task_runs_list_query_parser)
    def get(self):
        """获取任务运行列表."""
        parsed = _task_runs_list_query_parser.parse_args()
        query = validate_or_raise(TaskRunsListFiltersQuery, parsed)
        filters: TaskRunsListFilters = query.to_filters()

        def _execute():
            result = TaskRunsReadService().list_runs(filters)
            return self.success(
                data={
                    "items": [asdict(item) for item in result.items],
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                },
                message="获取任务运行列表成功",
            )

        return self.safe_call(
            _execute,
            module="task_runs",
            action="list_runs",
            public_error="获取任务运行列表失败",
            context={"endpoint": "task_runs_list"},
        )


@ns.route("/<string:run_id>")
class TaskRunDetailResource(BaseResource):
    """任务运行详情资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TaskRunDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, run_id: str):
        """获取任务运行详情."""

        def _execute():
            result = TaskRunsReadService().get_run_detail(run_id)
            return self.success(
                data={
                    "run": asdict(result.run),
                    "items": [asdict(item) for item in result.items],
                },
                message="获取任务运行详情成功",
            )

        return self.safe_call(
            _execute,
            module="task_runs",
            action="get_run_detail",
            public_error="获取任务运行详情失败",
            context={"run_id": run_id},
            expected_exceptions=(NotFoundError,),
        )


@ns.route("/<string:run_id>/error-logs")
class TaskRunErrorLogsResource(BaseResource):
    """任务运行错误日志资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", TaskRunErrorLogsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, run_id: str):
        """获取任务运行错误日志."""

        def _execute():
            result = TaskRunsReadService().get_run_error_logs(run_id)
            return self.success(
                data={
                    "run": asdict(result.run),
                    "items": [asdict(item) for item in result.items],
                    "error_count": result.error_count,
                },
                message="获取错误日志成功",
            )

        return self.safe_call(
            _execute,
            module="task_runs",
            action="get_run_error_logs",
            public_error="获取错误日志失败",
            context={"run_id": run_id},
            expected_exceptions=(NotFoundError,),
        )


@ns.route("/<string:run_id>/actions/cancel")
class TaskRunCancelResource(BaseResource):
    """任务运行取消资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", TaskRunCancelSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, run_id: str):
        """取消任务运行."""

        def _execute():
            success = task_runs_write_service.cancel_run(run_id)
            if not success:
                raise NotFoundError("取消任务失败,任务不存在或已结束")
            return self.success(message="任务已取消")

        return self.safe_call(
            _execute,
            module="task_runs",
            action="cancel_run",
            public_error="取消任务失败",
            context={"run_id": run_id},
            expected_exceptions=(NotFoundError,),
        )
