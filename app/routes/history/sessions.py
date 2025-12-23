"""鲸落 - 会话中心路由."""

from typing import Any, cast

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required
from sqlalchemy.sql.elements import ColumnElement

from app.constants import STATUS_SYNC_OPTIONS, SYNC_CATEGORIES, SYNC_TYPES, SyncStatus
from app.errors import NotFoundError, SystemError
from app.models.sync_session import SyncSession
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, view_required
from app.utils.pagination_utils import resolve_page, resolve_page_size
from app.utils.response_utils import jsonify_unified_success
from app.utils.route_safety import safe_route_call
from app.utils.structlog_config import log_info

history_sessions_bp = Blueprint("history_sessions", __name__)


@history_sessions_bp.route("/")
@login_required
@view_required
def index() -> str:
    """会话中心首页.

    Returns:
        渲染的会话中心页面.

    Raises:
        SystemError: 当页面加载失败时抛出.

    """

    def _render() -> str:
        return render_template(
            "history/sessions/sync-sessions.html",
            sync_type_options=SYNC_TYPES,
            sync_category_options=SYNC_CATEGORIES,
            status_options=STATUS_SYNC_OPTIONS,
        )

    return safe_route_call(
        _render,
        module="history_sessions",
        action="index",
        public_error="会话中心页面加载失败",
        context={"endpoint": "history_sessions_index"},
    )


@history_sessions_bp.route("/api/sessions")
@login_required
@view_required
def list_sessions() -> tuple[Response, int]:
    """获取同步会话列表 API.

    支持分页、排序和筛选(按类型、分类、状态).

    Returns:
        JSON 响应,包含会话列表和分页信息.

    Raises:
        SystemError: 当获取列表失败时抛出.

    Query Parameters:
        sync_type: 同步类型筛选,可选.
        sync_category: 同步分类筛选,可选.
        status: 状态筛选,可选.
        page: 页码,默认 1.
        page_size: 每页数量,默认 20,最大 100(兼容 limit/pageSize).
        sort: 排序字段,默认 'started_at'.
        order: 排序方向('asc'、'desc'),默认 'desc'.

    """

    def _execute() -> tuple[Response, int]:
        sync_type = (request.args.get("sync_type", "") or "").strip()
        sync_category = (request.args.get("sync_category", "") or "").strip()
        status = (request.args.get("status", "") or "").strip()
        page = resolve_page(request.args, default=1, minimum=1)
        limit = resolve_page_size(
            request.args,
            default=20,
            minimum=1,
            maximum=100,
            module="history_sessions",
            action="list_sessions",
        )
        sort_field = (request.args.get("sort", "started_at") or "started_at").strip()
        sort_order = (request.args.get("order", "desc") or "desc").lower()

        started_at_column = cast("ColumnElement[Any]", SyncSession.started_at)
        completed_at_column = cast("ColumnElement[Any]", SyncSession.completed_at)
        status_column = cast(ColumnElement[str], SyncSession.status)
        sync_type_column = cast(ColumnElement[str], SyncSession.sync_type)
        sync_category_column = cast(ColumnElement[str], SyncSession.sync_category)

        sortable_fields = {
            "started_at": started_at_column,
            "completed_at": completed_at_column,
            "status": status_column,
        }
        sort_column = sortable_fields.get(sort_field, started_at_column)
        ordering = sort_column.asc() if sort_order == "asc" else sort_column.desc()

        query = SyncSession.query
        if sync_type:
            query = query.filter(sync_type_column == sync_type)
        if sync_category:
            query = query.filter(sync_category_column == sync_category)
        if status:
            query = query.filter(status_column == status)

        query = query.order_by(ordering, SyncSession.id.desc())
        pagination = cast(Any, query).paginate(page=page, per_page=limit, error_out=False)

        sessions_data = [session.to_dict() for session in pagination.items]

        return jsonify_unified_success(
            data={
                "items": sessions_data,
                "total": pagination.total,
                "page": pagination.page,
                "pages": pagination.pages,
            },
            message="获取同步会话列表成功",
        )

    return safe_route_call(
        _execute,
        module="history_sessions",
        action="list_sessions",
        public_error="获取会话列表失败",
        context={"endpoint": "history_sessions_list"},
    )


@history_sessions_bp.route("/api/sessions/<session_id>")
@login_required
@view_required
def get_sync_session_detail(session_id: str) -> tuple[Response, int]:
    """获取同步会话详情 API.

    Args:
        session_id: 会话 ID.

    Returns:
        JSON 响应,包含会话详情、实例记录和进度百分比.

    Raises:
        NotFoundError: 当会话不存在时抛出.
        SystemError: 当获取详情失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            msg = "会话不存在"
            raise NotFoundError(msg)

        records = sync_session_service.get_session_records(session_id)
        records_data = [record.to_dict() for record in records]

        session_data = session.to_dict()
        session_data["instance_records"] = records_data
        session_data["progress_percentage"] = session.get_progress_percentage()

        return jsonify_unified_success(
            data={"session": session_data},
            message="获取同步会话详情成功",
        )

    return safe_route_call(
        _execute,
        module="history_sessions",
        action="get_sync_session_detail",
        public_error="获取会话详情失败",
        context={"session_id": session_id},
        expected_exceptions=(NotFoundError,),
    )


@history_sessions_bp.route("/api/sessions/<session_id>/cancel", methods=["POST"])
@login_required
@view_required
@require_csrf
def cancel_sync_session(session_id: str) -> tuple[Response, int]:
    """取消同步会话 API.

    Args:
        session_id: 会话 ID.

    Returns:
        JSON 响应.

    Raises:
        NotFoundError: 当会话不存在或已结束时抛出.
        SystemError: 当取消失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        success = sync_session_service.cancel_session(session_id)

        if success:
            log_info(
                "取消同步会话",
                module="history_sessions",
                user_id=current_user.id,
                session_id=session_id,
            )
            return jsonify_unified_success(message="会话已取消")
        msg = "取消会话失败,会话不存在或已结束"
        raise NotFoundError(msg)

    return safe_route_call(
        _execute,
        module="history_sessions",
        action="cancel_sync_session",
        public_error="取消会话失败",
        context={"session_id": session_id},
        expected_exceptions=(NotFoundError, SystemError),
    )


@history_sessions_bp.route("/api/sessions/<session_id>/error-logs", methods=["GET"])
@login_required
@view_required
def list_sync_session_errors(session_id: str) -> tuple[Response, int]:
    """获取同步会话错误日志 API.

    筛选出会话中所有失败的实例记录.

    Args:
        session_id: 会话 ID.

    Returns:
        JSON 响应,包含会话信息、错误记录列表和错误数量.

    Raises:
        NotFoundError: 当会话不存在时抛出.
        SystemError: 当获取错误日志失败时抛出.

    """

    def _execute() -> tuple[Response, int]:
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            msg = "会话不存在"
            raise NotFoundError(msg)

        records = sync_session_service.get_session_records(session_id)
        error_records = [record for record in records if record.status == SyncStatus.FAILED]
        error_records_data = [record.to_dict() for record in error_records]

        session_data = session.to_dict()

        return jsonify_unified_success(
            data={
                "session": session_data,
                "error_records": error_records_data,
                "error_count": len(error_records),
            },
            message="获取错误日志成功",
        )

    return safe_route_call(
        _execute,
        module="history_sessions",
        action="list_sync_session_errors",
        public_error="获取错误日志失败",
        context={"session_id": session_id},
        expected_exceptions=(NotFoundError,),
    )
