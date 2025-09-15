"""
泰摸鱼吧 - 统一日志管理路由
"""

from datetime import datetime, timedelta

from flask import Blueprint, Response, render_template, request
from flask_login import login_required  # type: ignore

from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.api_response import error_response, success_response
from app.utils.decorators import view_required
from app.utils.structlog_config import (
    get_system_logger,
    is_debug_logging_enabled,
    set_debug_logging_enabled,
)
from app.utils.timezone import now, utc_to_china

# 创建蓝图
logs_bp = Blueprint("logs", __name__)


@logs_bp.route("/")
@login_required  # type: ignore
@view_required  # type: ignore
def index() -> str:
    """统一日志中心首页"""
    # 获取日志数据用于模板渲染
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    level = request.args.get("level")
    module = request.args.get("module")
    q = request.args.get("q", "")
    hours = int(request.args.get("hours", 24))

    # 构建查询
    query = UnifiedLog.query

    # 时间过滤（使用东八区时间）
    if hours > 0:
        from datetime import timedelta
        start_time = now() - timedelta(hours=hours)
        query = query.filter(UnifiedLog.timestamp >= start_time)

    # 级别过滤
    if level:
        query = query.filter(UnifiedLog.level == level)

    # 模块过滤
    if module:
        query = query.filter(UnifiedLog.module == module)

    # 搜索过滤
    if q:
        query = query.filter(UnifiedLog.message.contains(q))

    # 分页查询
    logs = query.order_by(UnifiedLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    return render_template("logs/system_logs.html", logs=logs)


# ==================== 统一日志系统 API ====================


@logs_bp.route("/api/structlog/search", methods=["GET"])
@login_required  # type: ignore
def get_unified_logs() -> Response:
    """获取统一日志列表"""
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        level = request.args.get("level")
        module = request.args.get("module")
        q = request.args.get("q", "")
        hours = int(request.args.get("hours", 24))

        # 构建查询
        query = UnifiedLog.query

        # 时间过滤（使用东八区时间）
        if hours > 0:
            from datetime import timedelta

            start_time = now() - timedelta(hours=hours)
            query = query.filter(UnifiedLog.timestamp >= start_time)

        # 级别过滤
        if level:
            query = query.filter(UnifiedLog.level == level)

        # 模块过滤
        if module:
            query = query.filter(UnifiedLog.module == module)

        # 搜索过滤
        if q:
            query = query.filter(UnifiedLog.message.contains(q))

        # 分页查询
        logs = query.order_by(UnifiedLog.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

        # 构建响应数据（转换为东八区时间显示）
        logs_data = []
        for log in logs.items:
            # 转换为东八区时间
            china_timestamp = utc_to_china(log.timestamp)
            china_created_at = utc_to_china(log.created_at) if log.created_at else None

            logs_data.append(
                {
                    "id": log.id,
                    "timestamp": (china_timestamp.isoformat() if china_timestamp else None),
                    "level": log.level.value,
                    "module": log.module,
                    "message": log.message,
                    "context": log.context,
                    "traceback": log.traceback,
                    "created_at": (china_created_at.isoformat() if china_created_at else None),
                }
            )

        return success_response(
            {
                "logs": logs_data,
                "pagination": {
                    "page": logs.page,
                    "per_page": logs.per_page,
                    "total": logs.total,
                    "pages": logs.pages,
                    "has_next": logs.has_next,
                    "has_prev": logs.has_prev,
                    "next_num": logs.next_num,
                    "prev_num": logs.prev_num,
                },
            }
        )

    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("获取统一日志失败", module="logs", exception=e)
        return error_response("获取统一日志失败", 500)


@logs_bp.route("/api/structlog/stats", methods=["GET"])
@login_required  # type: ignore
def get_unified_log_stats() -> Response:
    """获取统一日志统计信息"""
    try:
        hours = int(request.args.get("hours", 24))
        stats = UnifiedLog.get_log_statistics(hours=hours)
        return success_response(stats)

    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("获取统一日志统计失败", module="logs", exception=e)
        return error_response("获取统一日志统计失败", 500)


@logs_bp.route("/api/structlog/errors", methods=["GET"])
@login_required  # type: ignore
def get_unified_error_logs() -> Response:
    """获取统一错误日志"""
    try:
        hours = int(request.args.get("hours", 24))
        limit = int(request.args.get("limit", 50))

        # 查询错误日志
        start_time = datetime.utcnow() - timedelta(hours=hours)
        error_logs = (
            UnifiedLog.query.filter(
                UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]),
                UnifiedLog.timestamp >= start_time,
            )
            .order_by(UnifiedLog.timestamp.desc())
            .limit(limit)
            .all()
        )

        logs_data = []
        for log in error_logs:
            logs_data.append(
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level.value,
                    "module": log.module,
                    "message": log.message,
                    "context": log.context,
                }
            )

        return success_response({"logs": logs_data})

    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("获取统一错误日志失败", module="logs", exception=e)
        return error_response("获取统一错误日志失败", 500)


@logs_bp.route("/api/structlog/modules", methods=["GET"])
@login_required  # type: ignore
def get_unified_log_modules() -> Response:
    """获取统一日志模块列表"""
    try:
        hours = int(request.args.get("hours", 24))
        modules = UnifiedLog.get_log_modules(hours=hours)
        module_list = [module.module for module in modules]
        return success_response(module_list)

    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("获取统一日志模块失败", module="logs", exception=e)
        return error_response("获取统一日志模块失败", 500)


@logs_bp.route("/api/structlog/detail/<int:log_id>", methods=["GET"])
@login_required  # type: ignore
def get_unified_log_detail(log_id: int) -> Response:
    """获取统一日志详情"""
    try:
        log = UnifiedLog.query.get_or_404(log_id)

        # 转换为东八区时间
        china_timestamp = utc_to_china(log.timestamp)
        china_created_at = utc_to_china(log.created_at) if log.created_at else None

        log_detail = {
            "id": log.id,
            "timestamp": china_timestamp.isoformat() if china_timestamp else None,
            "level": log.level.value,
            "module": log.module,
            "message": log.message,
            "context": log.context,
            "traceback": log.traceback,
            "created_at": china_created_at.isoformat() if china_created_at else None,
            "formatted_timestamp": (china_timestamp.strftime("%Y-%m-%d %H:%M:%S") if china_timestamp else None),
            "formatted_created_at": (china_created_at.strftime("%Y-%m-%d %H:%M:%S") if china_created_at else None),
        }

        return success_response(log_detail)

    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("获取日志详情失败", module="logs", exception=e)
        return error_response("获取日志详情失败", 500)


@logs_bp.route("/api/structlog/export", methods=["GET"])
@login_required  # type: ignore
def export_unified_logs() -> Response:
    """导出统一日志"""
    try:
        # 获取查询参数
        level = request.args.get("level")
        module = request.args.get("module")
        hours = int(request.args.get("hours", 24))
        format_type = request.args.get("format", "csv")

        # 构建查询
        query = UnifiedLog.query

        # 时间过滤（使用东八区时间）
        if hours > 0:
            start_time = now() - timedelta(hours=hours)
            query = query.filter(UnifiedLog.timestamp >= start_time)

        # 级别过滤
        if level:
            query = query.filter(UnifiedLog.level == level)

        # 模块过滤
        if module:
            query = query.filter(UnifiedLog.module == module)

        # 获取日志数据
        logs = query.order_by(UnifiedLog.timestamp.desc()).all()

        if format_type == "csv":
            import csv
            import io

            from flask import make_response

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow(["时间", "级别", "模块", "消息", "上下文", "堆栈追踪", "创建时间"])

            # 写入数据（转换为东八区时间显示）
            for log in logs:
                # 转换为东八区时间
                china_timestamp = utc_to_china(log.timestamp)
                china_created_at = utc_to_china(log.created_at) if log.created_at else None

                writer.writerow(
                    [
                        (china_timestamp.strftime("%Y-%m-%d %H:%M:%S") if china_timestamp else ""),
                        log.level.value,
                        log.module,
                        log.message,
                        log.context,
                        log.traceback,
                        (china_created_at.strftime("%Y-%m-%d %H:%M:%S") if china_created_at else ""),
                    ]
                )

            response = make_response(output.getvalue())
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            response.headers["Content-Disposition"] = "attachment; filename=unified_logs.csv"
            return response

        if format_type == "json":
            logs_data = []
            for log in logs:
                # 转换为东八区时间
                china_timestamp = utc_to_china(log.timestamp)
                china_created_at = utc_to_china(log.created_at) if log.created_at else None

                logs_data.append(
                    {
                        "id": log.id,
                        "timestamp": (china_timestamp.isoformat() if china_timestamp else None),
                        "level": log.level.value,
                        "module": log.module,
                        "message": log.message,
                        "context": log.context,
                        "traceback": log.traceback,
                        "created_at": (china_created_at.isoformat() if china_created_at else None),
                    }
                )

            return success_response(
                {
                    "data": {
                        "logs": logs_data,
                        "total": len(logs),
                        "exported_at": now().isoformat(),
                    }
                }
            )
        return error_response("Unsupported format", 400)

    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("导出统一日志失败", module="logs", exception=e)
        return error_response("导出统一日志失败", 500)


@logs_bp.route("/api/debug-status", methods=["GET"])
@login_required  # type: ignore
def get_debug_status() -> Response:
    """获取DEBUG日志状态"""
    try:
        enabled = is_debug_logging_enabled()
        return success_response({"enabled": enabled, "status": "启用" if enabled else "关闭"})
    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("获取DEBUG日志状态失败", module="logs", exception=e)
        return error_response("获取DEBUG日志状态失败", 500)


@logs_bp.route("/api/debug-toggle", methods=["POST"])
@login_required  # type: ignore
def toggle_debug_logging() -> Response:
    """切换DEBUG日志开关"""
    try:
        current_enabled = is_debug_logging_enabled()
        new_enabled = not current_enabled

        # 设置新的DEBUG日志状态
        set_debug_logging_enabled(new_enabled)

        # 记录状态变更日志
        from app.utils.structlog_config import log_info

        log_info(f"DEBUG日志已{'启用' if new_enabled else '关闭'}", module="system")

        return success_response(
            {
                "enabled": new_enabled,
                "status": "启用" if new_enabled else "关闭",
                "message": f"DEBUG日志已{'启用' if new_enabled else '关闭'}",
            }
        )
    except Exception as e:
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("切换DEBUG日志状态失败", module="logs", exception=e)
        return error_response("切换DEBUG日志状态失败", 500)


@logs_bp.route("/api/logs/frontend", methods=["POST"])
def frontend_log() -> Response:
    """接收前端日志并记录到structlog系统"""
    try:
        data = request.get_json()
        if not data:
            return error_response("无效的请求数据", 400)

        # 获取日志信息
        level = data.get("level", "info")
        message = data.get("message", "")
        module = data.get("module", "frontend")
        context = data.get("context", {})

        # 获取系统日志记录器
        system_logger = get_system_logger()

        # 根据级别记录日志
        if level == "error":
            system_logger.error(message, module=module, **context)
        elif level == "warning":
            system_logger.warning(message, module=module, **context)
        elif level == "info":
            system_logger.info(message, module=module, **context)
        elif level == "debug":
            system_logger.debug(message, module=module, **context)
        else:
            system_logger.info(message, module=module, **context)

        return success_response({"message": "日志记录成功"})

    except Exception as e:
        # 使用标准logging避免循环依赖
        from app.utils.structlog_config import get_system_logger

        system_logger = get_system_logger()
        system_logger.error("记录前端日志失败", module="logs", exception=e)
        return error_response("记录前端日志失败", 500)
