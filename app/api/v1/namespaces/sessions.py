"""Sessions namespace (Phase 4C 同步会话)."""

from __future__ import annotations

from typing import ClassVar

from flask_login import current_user
from flask_restx import Namespace, fields, marshal

from app.api.v1.models.envelope import get_error_envelope_model, make_success_envelope_model
from app.api.v1.resources.base import BaseResource
from app.api.v1.resources.decorators import api_login_required, api_permission_required
from app.api.v1.resources.query_parsers import new_parser
from app.api.v1.restx_models.history import (
    SYNC_SESSION_DETAIL_RESPONSE_FIELDS,
    SYNC_SESSION_ERROR_LOGS_RESPONSE_FIELDS,
    SYNC_SESSION_ITEM_FIELDS,
)
from app.errors import NotFoundError
from app.services.history_sessions.history_sessions_read_service import HistorySessionsReadService
from app.services.sync_session_service import sync_session_service
from app.types.history_sessions import HistorySessionsListFilters
from app.utils.decorators import require_csrf
from app.utils.structlog_config import log_info

ns = Namespace("history_sessions", description="同步会话")

ErrorEnvelope = get_error_envelope_model(ns)

HistorySessionsListData = ns.model(
    "HistorySessionsListData",
    {
        "items": fields.Raw(required=True),
        "total": fields.Integer(required=True),
        "page": fields.Integer(required=True),
        "pages": fields.Integer(required=True),
    },
)
HistorySessionsListSuccessEnvelope = make_success_envelope_model(
    ns,
    "HistorySessionsListSuccessEnvelope",
    HistorySessionsListData,
)

HistorySessionDetailSuccessEnvelope = make_success_envelope_model(ns, "HistorySessionDetailSuccessEnvelope")
HistorySessionErrorLogsSuccessEnvelope = make_success_envelope_model(ns, "HistorySessionErrorLogsSuccessEnvelope")
HistorySessionCancelSuccessEnvelope = make_success_envelope_model(ns, "HistorySessionCancelSuccessEnvelope")

_history_sessions_list_query_parser = new_parser()
_history_sessions_list_query_parser.add_argument("sync_type", type=str, default="", location="args")
_history_sessions_list_query_parser.add_argument("sync_category", type=str, default="", location="args")
_history_sessions_list_query_parser.add_argument("status", type=str, default="", location="args")
_history_sessions_list_query_parser.add_argument("page", type=int, default=1, location="args")
_history_sessions_list_query_parser.add_argument("limit", type=int, default=20, location="args")
_history_sessions_list_query_parser.add_argument("sort", type=str, default="started_at", location="args")
_history_sessions_list_query_parser.add_argument("order", type=str, default="desc", location="args")


@ns.route("")
class HistorySessionsListResource(BaseResource):
    """同步会话列表资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", HistorySessionsListSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @ns.expect(_history_sessions_list_query_parser)
    def get(self):
        """获取同步会话列表."""
        parsed = _history_sessions_list_query_parser.parse_args()
        sync_type = str(parsed.get("sync_type") or "").strip()
        sync_category = str(parsed.get("sync_category") or "").strip()
        status = str(parsed.get("status") or "").strip()
        page = max(int(parsed.get("page") or 1), 1)
        limit = int(parsed.get("limit") or 20)
        limit = max(min(limit, 100), 1)
        sort_field = str(parsed.get("sort") or "started_at").strip() or "started_at"
        sort_order = str(parsed.get("order") or "desc").lower()
        if sort_order not in {"asc", "desc"}:
            sort_order = "desc"

        filters = HistorySessionsListFilters(
            sync_type=sync_type,
            sync_category=sync_category,
            status=status,
            page=page,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
        )

        def _execute():
            result = HistorySessionsReadService().list_sessions(filters)
            items = marshal(result.items, SYNC_SESSION_ITEM_FIELDS)
            return self.success(
                data={
                    "items": items,
                    "total": result.total,
                    "page": result.page,
                    "pages": result.pages,
                },
                message="获取同步会话列表成功",
            )

        return self.safe_call(
            _execute,
            module="history_sessions",
            action="list_sessions",
            public_error="获取会话列表失败",
            context={"endpoint": "history_sessions_list"},
        )


@ns.route("/<string:session_id>")
class HistorySessionDetailResource(BaseResource):
    """同步会话详情资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", HistorySessionDetailSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, session_id: str):
        """获取同步会话详情."""

        def _execute():
            result = HistorySessionsReadService().get_session_detail(session_id)
            payload = marshal(result, SYNC_SESSION_DETAIL_RESPONSE_FIELDS)
            return self.success(data=payload, message="获取同步会话详情成功")

        return self.safe_call(
            _execute,
            module="history_sessions",
            action="get_sync_session_detail",
            public_error="获取会话详情失败",
            context={"session_id": session_id},
            expected_exceptions=(NotFoundError,),
        )


@ns.route("/<string:session_id>/error-logs")
class HistorySessionErrorLogsResource(BaseResource):
    """同步会话错误日志资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("view")]

    @ns.response(200, "OK", HistorySessionErrorLogsSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    def get(self, session_id: str):
        """获取会话错误日志."""

        def _execute():
            result = HistorySessionsReadService().get_session_error_logs(session_id)
            payload = marshal(result, SYNC_SESSION_ERROR_LOGS_RESPONSE_FIELDS)
            return self.success(data=payload, message="获取错误日志成功")

        return self.safe_call(
            _execute,
            module="history_sessions",
            action="list_sync_session_errors",
            public_error="获取错误日志失败",
            context={"session_id": session_id},
            expected_exceptions=(NotFoundError,),
        )


@ns.route("/<string:session_id>/actions/cancel")
class HistorySessionCancelResource(BaseResource):
    """同步会话取消资源."""

    method_decorators: ClassVar[list] = [api_login_required, api_permission_required("admin")]

    @ns.response(200, "OK", HistorySessionCancelSuccessEnvelope)
    @ns.response(401, "Unauthorized", ErrorEnvelope)
    @ns.response(403, "Forbidden", ErrorEnvelope)
    @ns.response(404, "Not Found", ErrorEnvelope)
    @ns.response(500, "Internal Server Error", ErrorEnvelope)
    @require_csrf
    def post(self, session_id: str):
        """取消同步会话."""

        def _execute():
            success = sync_session_service.cancel_session(session_id)
            if not success:
                raise NotFoundError("取消会话失败,会话不存在或已结束")

            log_info(
                "取消同步会话",
                module="history_sessions",
                user_id=getattr(current_user, "id", None),
                session_id=session_id,
            )
            return self.success(message="会话已取消")

        return self.safe_call(
            _execute,
            module="history_sessions",
            action="cancel_sync_session",
            public_error="取消会话失败",
            context={"session_id": session_id},
            expected_exceptions=(NotFoundError,),
        )
