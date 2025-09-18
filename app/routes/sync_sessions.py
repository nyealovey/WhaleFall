"""
鲸落 - 同步会话管理路由
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.services.sync_session_service import sync_session_service
from app.utils.decorators import view_required
from app.utils.structlog_config import get_system_logger, log_error, log_info

# 创建蓝图
sync_sessions_bp = Blueprint("sync_sessions", __name__, url_prefix="/sync_sessions")

# 获取日志记录器
system_logger = get_system_logger()


@sync_sessions_bp.route("/")
@login_required
@view_required
def index() -> str:
    """同步会话管理首页"""
    try:
        return render_template("sync_sessions/management.html")
    except Exception as e:
        log_error(
            f"访问同步会话管理页面失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
        )
        return render_template("sync_sessions/management.html", error="页面加载失败")


@sync_sessions_bp.route("/api/sessions")
@login_required
@view_required
def api_list_sessions() -> tuple[dict, int]:
    """获取同步会话列表 API"""
    try:
        # 获取查询参数
        sync_type = request.args.get("sync_type", "")
        sync_category = request.args.get("sync_category", "")
        status = request.args.get("status", "")
        limit = int(request.args.get("limit", 50))

        # 构建查询
        sessions = sync_session_service.get_recent_sessions(limit)

        # 过滤结果
        if sync_type:
            sessions = [s for s in sessions if s.sync_type == sync_type]
        if sync_category:
            sessions = [s for s in sessions if s.sync_category == sync_category]
        if status:
            sessions = [s for s in sessions if s.status == status]

        # 转换为字典
        sessions_data = [session.to_dict() for session in sessions]

        log_info(
            "获取同步会话列表",
            module="sync_sessions",
            user_id=current_user.id,
            session_count=len(sessions_data),
            filters={
                "sync_type": sync_type,
                "sync_category": sync_category,
                "status": status,
            },
        )

        return jsonify({"success": True, "data": sessions_data, "total": len(sessions_data)})

    except Exception as e:
        log_error(
            f"获取同步会话列表失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
        )
        return (
            jsonify({"success": False, "message": "获取会话列表失败", "error": str(e)}),
            500,
        )


@sync_sessions_bp.route("/api/sessions/<session_id>")
@login_required
@view_required
def api_get_session_detail(session_id: str) -> tuple[dict, int]:
    """获取同步会话详情 API"""
    try:
        # 获取会话信息
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            return jsonify({"success": False, "message": "会话不存在"}), 404

        # 获取实例记录
        records = sync_session_service.get_session_records(session_id)
        records_data = [record.to_dict() for record in records]

        # 构建响应数据
        session_data = session.to_dict()
        session_data["instance_records"] = records_data
        session_data["progress_percentage"] = session.get_progress_percentage()

        # 移除用户查看操作的日志记录

        return jsonify({"success": True, "data": session_data})

    except Exception as e:
        log_error(
            f"获取同步会话详情失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        return (
            jsonify({"success": False, "message": "获取会话详情失败", "error": str(e)}),
            500,
        )


@sync_sessions_bp.route("/api/sessions/<session_id>/cancel", methods=["POST"])
@login_required
@view_required
def api_cancel_session(session_id: str) -> tuple[dict, int]:
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
            return jsonify({"success": True, "message": "会话已取消"})
        return (
            jsonify({"success": False, "message": "取消会话失败，会话不存在或已结束"}),
            400,
        )

    except Exception as e:
        log_error(
            f"取消同步会话失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        return (
            jsonify({"success": False, "message": "取消会话失败", "error": str(e)}),
            500,
        )


@sync_sessions_bp.route("/api/sessions/<session_id>/error-logs", methods=["GET"])
@login_required
@view_required
def api_get_error_logs(session_id: str) -> tuple[dict, int]:
    """获取同步会话错误日志 API"""
    try:
        # 获取会话信息
        session = sync_session_service.get_session_by_id(session_id)
        if not session:
            return (
                jsonify({"success": False, "message": "会话不存在"}),
                404,
            )

        # 获取所有实例记录
        records = sync_session_service.get_session_records(session_id)

        # 筛选出失败的记录
        error_records = [record for record in records if record.status == "failed"]

        # 转换为字典格式
        error_records_data = [record.to_dict() for record in error_records]

        # 构建响应数据
        session_data = session.to_dict()

        return jsonify(
            {
                "success": True,
                "data": {
                    "session": session_data,
                    "error_records": error_records_data,
                    "error_count": len(error_records),
                },
            }
        )

    except Exception as e:
        log_error(
            f"获取同步会话错误日志失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
            session_id=session_id,
        )
        return (
            jsonify({"success": False, "message": "获取错误日志失败", "error": str(e)}),
            500,
        )


@sync_sessions_bp.route("/api/statistics")
@login_required
@view_required
def api_get_statistics() -> tuple[dict, int]:
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

        return jsonify({"success": True, "data": statistics})

    except Exception as e:
        log_error(
            f"获取同步统计信息失败: {str(e)}",
            module="sync_sessions",
            user_id=current_user.id,
        )
        return (
            jsonify({"success": False, "message": "获取统计信息失败", "error": str(e)}),
            500,
        )
