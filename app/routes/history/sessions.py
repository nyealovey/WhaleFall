
"""鲸落 - 会话中心路由."""

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app.constants import STATUS_SYNC_OPTIONS, SYNC_CATEGORIES, SYNC_TYPES, SyncStatus
from app.errors import NotFoundError, SystemError
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import require_csrf, view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

history_sessions_bp = Blueprint("history_sessions", __name__)


@history_sessions_bp.route("/")
@login_required
@view_required
def index() -> str:
    """会话中心首页。.

    Returns:
        渲染的会话中心页面。

    Raises:
        SystemError: 当页面加载失败时抛出。

    """
    try:
        return render_template(
            "history/sessions/sync-sessions.html",
            sync_type_options=SYNC_TYPES,
            sync_category_options=SYNC_CATEGORIES,
            status_options=STATUS_SYNC_OPTIONS,
        )
    except Exception as e:
        log_error(
            f"访问会话中心页面失败: {e!s}",
            module="history_sessions",
            user_id=current_user.id,
        )
        msg = "会话中心页面加载失败"
        raise SystemError(msg) from e


@history_sessions_bp.route("/api/sessions")
@login_required
@view_required
def list_sessions() -> Response:
    """获取同步会话列表 API。.

    支持分页、排序和筛选（按类型、分类、状态）。

    Returns:
        JSON 响应，包含会话列表和分页信息。

    Raises:
        SystemError: 当获取列表失败时抛出。

    Query Parameters:
        sync_type: 同步类型筛选，可选。
        sync_category: 同步分类筛选，可选。
        status: 状态筛选，可选。
        page: 页码，默认 1。
        limit: 每页数量，默认 20，最大 100。
        sort: 排序字段，默认 'started_at'。
        order: 排序方向（'asc'、'desc'），默认 'desc'。

    """
    try:
        sync_type = (request.args.get("sync_type", "") or "").strip()
        sync_category = (request.args.get("sync_category", "") or "").strip()
        status = (request.args.get("status", "") or "").strip()
        page = max(int(request.args.get("page", 1)), 1)
        limit = int(request.args.get("limit", request.args.get("per_page", 20)))
        limit = max(1, min(limit, 100))
        sort_field = (request.args.get("sort", "started_at") or "started_at").strip()
        sort_order = (request.args.get("order", "desc") or "desc").lower()

        all_sessions = sync_session_service.get_recent_sessions(1000)

        filtered_sessions = all_sessions
        if sync_type:
            filtered_sessions = [s for s in filtered_sessions if s.sync_type == sync_type]
        if sync_category:
            filtered_sessions = [s for s in filtered_sessions if s.sync_category == sync_category]
        if status:
            filtered_sessions = [s for s in filtered_sessions if s.status == status]

        reverse = sort_order != "asc"
        sort_key_map = {
            "started_at": lambda s: s.started_at or "",
            "completed_at": lambda s: s.completed_at or "",
            "status": lambda s: s.status or "",
        }
        sort_key = sort_key_map.get(sort_field, sort_key_map["started_at"])
        filtered_sessions.sort(key=sort_key, reverse=reverse)

        total = len(filtered_sessions)
        start = (page - 1) * limit
        end = start + limit
        sessions_page = filtered_sessions[start:end]
        sessions_data = [session.to_dict() for session in sessions_page]
        total_pages = (total + limit - 1) // limit

        return jsonify_unified_success(
            data={
                "items": sessions_data,
                "total": total,
                "page": page,
                "pages": total_pages,
            },
            message="获取同步会话列表成功",
        )

    except Exception as e:
        log_error(
            f"获取同步会话列表失败: {e!s}",
            module="history_sessions",
            user_id=current_user.id,
        )
        msg = "获取会话列表失败"
        raise SystemError(msg) from e


@history_sessions_bp.route("/api/sessions/<session_id>")
@login_required
@view_required
def get_sync_session_detail(session_id: str) -> Response:
    """获取同步会话详情 API。.

    Args:
        session_id: 会话 ID。

    Returns:
        JSON 响应，包含会话详情、实例记录和进度百分比。

    Raises:
        NotFoundError: 当会话不存在时抛出。
        SystemError: 当获取详情失败时抛出。

    """
    try:
        # 获取会话信息
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            msg = "会话不存在"
            raise NotFoundError(msg)

        # 获取实例记录
        records = sync_session_service.get_session_records(session_id)
        records_data = [record.to_dict() for record in records]

        # 构建响应数据
        session_data = session.to_dict()
        session_data["instance_records"] = records_data
        session_data["progress_percentage"] = session.get_progress_percentage()

        # 移除用户查看操作的日志记录

        return jsonify_unified_success(
            data={"session": session_data},
            message="获取同步会话详情成功",
        )

    except Exception as e:
        log_error(
            f"获取同步会话详情失败: {e!s}",
            module="history_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        msg = "获取会话详情失败"
        raise SystemError(msg) from e


@history_sessions_bp.route("/api/sessions/<session_id>/cancel", methods=["POST"])
@login_required
@view_required
@require_csrf
def cancel_sync_session(session_id: str) -> Response:
    """取消同步会话 API。.

    Args:
        session_id: 会话 ID。

    Returns:
        JSON 响应。

    Raises:
        NotFoundError: 当会话不存在或已结束时抛出。
        SystemError: 当取消失败时抛出。

    """
    try:
        success = sync_session_service.cancel_session(session_id)

        if success:
            log_info(
                "取消同步会话",
                module="history_sessions",
                user_id=current_user.id,
                session_id=session_id,
            )
            return jsonify_unified_success(message="会话已取消")
        msg = "取消会话失败，会话不存在或已结束"
        raise NotFoundError(msg)

    except Exception as e:
        log_error(
            f"取消同步会话失败: {e!s}",
            module="history_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        msg = "取消会话失败"
        raise SystemError(msg) from e


@history_sessions_bp.route("/api/sessions/<session_id>/error-logs", methods=["GET"])
@login_required
@view_required
def list_sync_session_errors(session_id: str) -> Response:
    """获取同步会话错误日志 API。.

    筛选出会话中所有失败的实例记录。

    Args:
        session_id: 会话 ID。

    Returns:
        JSON 响应，包含会话信息、错误记录列表和错误数量。

    Raises:
        NotFoundError: 当会话不存在时抛出。
        SystemError: 当获取错误日志失败时抛出。

    """
    try:
        # 获取会话信息
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            msg = "会话不存在"
            raise NotFoundError(msg)

        # 获取所有实例记录
        records = sync_session_service.get_session_records(session_id)

        # 筛选出失败的记录
        error_records = [record for record in records if record.status == SyncStatus.FAILED]

        # 转换为字典格式
        error_records_data = [record.to_dict() for record in error_records]

        # 构建响应数据
        session_data = session.to_dict()

        return jsonify_unified_success(
            data={
                "session": session_data,
                "error_records": error_records_data,
                "error_count": len(error_records),
            },
            message="获取错误日志成功",
        )

    except Exception as e:
        log_error(
            f"获取同步会话错误日志失败: {e!s}",
            module="history_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        msg = "获取错误日志失败"
        raise SystemError(msg) from e
