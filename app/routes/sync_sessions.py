
"""
鲸落 - 会话中心路由
"""

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app.errors import NotFoundError, SystemError
from app.services.sync_session_service import sync_session_service
from app.utils.decorators import view_required
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

sync_sessions_bp = Blueprint("sync_sessions", __name__)


@sync_sessions_bp.route("/")
@login_required
@view_required
def index() -> str:
    """会话中心首页"""
    try:
        return render_template("history/sync_sessions.html")
    except Exception as e:
        log_error(
            f"访问会话中心页面失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
        )
        raise SystemError("会话中心页面加载失败") from e


@sync_sessions_bp.route("/api/sessions")
@login_required
@view_required
def api_list_sessions() -> Response:
    """获取同步会话列表 API"""
    try:
        # 获取查询参数
        sync_type = request.args.get("sync_type", "")
        sync_category = request.args.get("sync_category", "")
        status = request.args.get("status", "")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        
        # 获取所有会话（这里可能需要根据实际情况调整获取数量）
        all_sessions = sync_session_service.get_recent_sessions(1000)  # 获取更多数据用于分页

        # 过滤结果
        filtered_sessions = all_sessions
        if sync_type and sync_type.strip():
            filtered_sessions = [s for s in filtered_sessions if s.sync_type == sync_type]
        if sync_category and sync_category.strip():
            filtered_sessions = [s for s in filtered_sessions if s.sync_category == sync_category]
        if status and status.strip():
            filtered_sessions = [s for s in filtered_sessions if s.status == status]

        # 计算分页
        total = len(filtered_sessions)
        start = (page - 1) * per_page
        end = start + per_page
        sessions_page = filtered_sessions[start:end]

        # 转换为字典
        sessions_data = [session.to_dict() for session in sessions_page]
        
        # 计算分页信息
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages

        pagination_info = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": total_pages,
            "has_prev": has_prev,
            "has_next": has_next,
            "prev_num": page - 1 if has_prev else None,
            "next_num": page + 1 if has_next else None
        }

        return jsonify_unified_success(
            data={
                "sessions": sessions_data,
                "total": total,
                "pagination": pagination_info,
            },
            message="获取同步会话列表成功",
        )

    except Exception as e:
        log_error(
            f"获取同步会话列表失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
        )
        raise SystemError("获取会话列表失败") from e


@sync_sessions_bp.route("/api/sessions/<session_id>")
@login_required
@view_required
def api_get_session_detail(session_id: str) -> Response:
    """获取同步会话详情 API"""
    try:
        # 获取会话信息
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            raise NotFoundError("会话不存在")

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
            f"获取同步会话详情失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        raise SystemError("获取会话详情失败") from e


@sync_sessions_bp.route("/api/sessions/<session_id>/cancel", methods=["POST"])
@login_required
@view_required
def api_cancel_session(session_id: str) -> Response:
    """取消同步会话 API"""
    try:
        success = sync_session_service.cancel_session(session_id)

        if success:
            log_info(
                "取消同步会话",
                module="sync_sessions",
                user_id=current_user.id,
                session_id=session_id,
            )
            return jsonify_unified_success(message="会话已取消")
        raise NotFoundError("取消会话失败，会话不存在或已结束")

    except Exception as e:
        log_error(
            f"取消同步会话失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        raise SystemError("取消会话失败") from e


@sync_sessions_bp.route("/api/sessions/<session_id>/error-logs", methods=["GET"])
@login_required
@view_required
def api_get_error_logs(session_id: str) -> Response:
    """获取同步会话错误日志 API"""
    try:
        # 获取会话信息
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            raise NotFoundError("会话不存在")

        # 获取所有实例记录
        records = sync_session_service.get_session_records(session_id)

        # 筛选出失败的记录
        error_records = [record for record in records if record.status == "failed"]

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
            f"获取同步会话错误日志失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        raise SystemError("获取错误日志失败") from e


@sync_sessions_bp.route("/api/statistics")
@login_required
@view_required
def api_get_statistics() -> Response:
    """获取同步统计信息 API"""
    try:
        # 获取各种类型的会话统计
        scheduled_sessions = sync_session_service.get_sessions_by_type("scheduled_task", 100)
        manual_sessions = sync_session_service.get_sessions_by_type("manual_batch", 100)

        # 计算统计信息
        total_sessions = len(scheduled_sessions) + len(manual_sessions)
        running_sessions = len([s for s in scheduled_sessions + manual_sessions if s.status == "running"])
        completed_sessions = len([s for s in scheduled_sessions + manual_sessions if s.status == "completed"])
        failed_sessions = len([s for s in scheduled_sessions + manual_sessions if s.status == "failed"])

        # 按分类统计
        account_sessions = len([s for s in scheduled_sessions + manual_sessions if s.sync_category == "account"])
        capacity_sessions = len([s for s in scheduled_sessions + manual_sessions if s.sync_category == "capacity"])
        config_sessions = len([s for s in scheduled_sessions + manual_sessions if s.sync_category == "config"])
        other_sessions = len([s for s in scheduled_sessions + manual_sessions if s.sync_category == "other"])

        statistics = {
            "total_sessions": total_sessions,
            "running_sessions": running_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "scheduled_sessions": len(scheduled_sessions),
            "manual_sessions": len(manual_sessions),
            "by_category": {
                "account": account_sessions,
                "capacity": capacity_sessions,
                "config": config_sessions,
                "other": other_sessions,
            },
        }

        log_info(
            "获取同步统计信息",
            module="sync_sessions",
            user_id=current_user.id,
            statistics=statistics,
        )

        return jsonify_unified_success(
            data=statistics,
            message="获取同步统计信息成功",
        )

    except Exception as e:
        log_error(
            f"获取同步统计信息失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
        )
        raise SystemError("获取统计信息失败") from e
