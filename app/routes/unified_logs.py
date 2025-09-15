"""
泰摸鱼吧 - 统一日志系统API路由
提供日志查询、展示和管理的RESTful API
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import asc, desc, or_

from app import db
from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.api_response import error_response, success_response
from app.utils.structlog_config import get_logger, log_error, log_info
from app.utils.timezone import now

# 创建蓝图
unified_logs_bp = Blueprint("unified_logs", __name__, url_prefix="/unified-logs")

# 获取日志记录器
logger = get_logger("api")


@unified_logs_bp.route("/")
@login_required
def logs_dashboard():
    """日志中心仪表板"""
    try:
        return render_template("logs/dashboard.html")
    except Exception as e:
        log_error("Failed to render logs dashboard", module="unified_logs", error=str(e))
        return error_response("Failed to load logs dashboard", 500)


@unified_logs_bp.route("/api/search", methods=["GET"])
@login_required
def search_logs():
    """搜索日志API"""
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        level = request.args.get("level")
        module = request.args.get("module")
        search_term = request.args.get("q", "").strip()
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        sort_by = request.args.get("sort_by", "timestamp")
        sort_order = request.args.get("sort_order", "desc")

        # 构建查询
        query = UnifiedLog.query

        # 时间范围过滤
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                query = query.filter(UnifiedLog.timestamp >= start_dt)
            except ValueError:
                return error_response("Invalid start_time format", 400)

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                query = query.filter(UnifiedLog.timestamp <= end_dt)
            except ValueError:
                return error_response("Invalid end_time format", 400)

        # 默认时间范围：最近24小时
        if not start_time and not end_time:
            default_start = now() - timedelta(hours=24)
            query = query.filter(UnifiedLog.timestamp >= default_start)

        # 级别过滤
        if level:
            try:
                log_level = LogLevel(level.upper())
                query = query.filter(UnifiedLog.level == log_level)
            except ValueError:
                return error_response("Invalid log level", 400)

        # 模块过滤
        if module:
            query = query.filter(UnifiedLog.module.like(f"%{module}%"))

        # 关键词搜索
        if search_term:
            search_filter = or_(
                UnifiedLog.message.like(f"%{search_term}%"),
                UnifiedLog.context.like(f"%{search_term}%"),
            )
            query = query.filter(search_filter)

        # 排序
        if sort_by == "timestamp":
            order_column = UnifiedLog.timestamp
        elif sort_by == "level":
            order_column = UnifiedLog.level
        elif sort_by == "module":
            order_column = UnifiedLog.module
        else:
            order_column = UnifiedLog.timestamp

        if sort_order == "asc":
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        # 分页
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 构建响应
        logs = []
        for log_entry in pagination.items:
            logs.append(log_entry.to_dict())

        response_data = {
            "logs": logs,
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
                "prev_num": pagination.prev_num if pagination.has_prev else None,
                "next_num": pagination.next_num if pagination.has_next else None,
            },
        }

        return success_response(response_data)

    except Exception as e:
        log_error("Failed to search logs", module="unified_logs", error=str(e))
        return error_response("Failed to search logs", 500)


@unified_logs_bp.route("/api/statistics", methods=["GET"])
@login_required
def get_log_statistics():
    """获取日志统计信息API"""
    try:
        hours = int(request.args.get("hours", 24))

        stats = UnifiedLog.get_log_statistics(hours=hours)

        log_info(
            "Log statistics retrieved",
            module="unified_logs",
            hours=hours,
            total_logs=stats["total_logs"],
        )

        return success_response(stats)

    except Exception as e:
        log_error("Failed to get log statistics", module="unified_logs", error=str(e))
        return error_response("Failed to get log statistics", 500)


@unified_logs_bp.route("/api/errors", methods=["GET"])
@login_required
def get_error_logs():
    """获取错误日志API"""
    try:
        hours = int(request.args.get("hours", 24))
        limit = int(request.args.get("limit", 50))

        error_logs = UnifiedLog.get_error_logs(hours=hours, limit=limit)

        logs = [log.to_dict() for log in error_logs]

        return success_response({"logs": logs})

    except Exception as e:
        log_error("Failed to get error logs", module="unified_logs", error=str(e))
        return error_response("Failed to get error logs", 500)


@unified_logs_bp.route("/api/modules", methods=["GET"])
@login_required
def get_log_modules():
    """获取日志模块列表API"""
    try:
        from sqlalchemy import distinct

        # 获取所有模块
        modules = db.session.query(distinct(UnifiedLog.module).label("module")).order_by(UnifiedLog.module).all()

        module_list = [module.module for module in modules]

        return success_response({"modules": module_list})

    except Exception as e:
        log_error("Failed to get log modules", module="unified_logs", error=str(e))
        return error_response("Failed to get log modules", 500)


@unified_logs_bp.route("/api/export", methods=["GET"])
@login_required
def export_logs():
    """导出日志API"""
    try:
        format_type = request.args.get("format", "json")
        level = request.args.get("level")
        module = request.args.get("module")
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        limit = int(request.args.get("limit", 1000))

        # 构建查询
        query = UnifiedLog.query

        # 时间范围过滤
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            query = query.filter(UnifiedLog.timestamp >= start_dt)

        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            query = query.filter(UnifiedLog.timestamp <= end_dt)

        # 级别过滤
        if level:
            log_level = LogLevel(level.upper())
            query = query.filter(UnifiedLog.level == log_level)

        # 模块过滤
        if module:
            query = query.filter(UnifiedLog.module.like(f"%{module}%"))

        # 先排序，再限制数量
        query = query.order_by(desc(UnifiedLog.timestamp))

        # 限制数量
        query = query.limit(limit)

        # 获取日志
        logs = query.all()

        if format_type == "csv":
            # CSV格式导出
            import csv
            import io
            from datetime import datetime

            output = io.StringIO()
            writer = csv.writer(output)

            # 写入表头
            writer.writerow(
                [
                    "ID",
                    "时间戳",
                    "级别",
                    "模块",
                    "消息",
                    "堆栈追踪",
                    "上下文",
                    "创建时间"
                ]
            )

            # 写入数据
            for log in logs:
                # 格式化时间戳（转换为东八区时间）
                timestamp_str = ""
                if log.timestamp:
                    from app.utils.timezone import utc_to_china
                    china_time = utc_to_china(log.timestamp)
                    timestamp_str = china_time.strftime("%Y-%m-%d %H:%M:%S")
                
                created_at_str = ""
                if log.created_at:
                    from app.utils.timezone import utc_to_china
                    china_created_at = utc_to_china(log.created_at)
                    created_at_str = china_created_at.strftime("%Y-%m-%d %H:%M:%S")

                # 处理上下文数据，提取关键信息
                context_str = ""
                if log.context and isinstance(log.context, dict):
                    # 提取有意义的上下文信息
                    context_parts = []
                    for key, value in log.context.items():
                        if value is not None and value != "" and key not in ['request_id', 'user_id', 'url', 'method', 'ip_address', 'user_agent']:
                            context_parts.append(f"{key}: {value}")
                    context_str = "; ".join(context_parts)

                writer.writerow(
                    [
                        log.id,
                        timestamp_str,
                        log.level.value if log.level else "",
                        log.module or "",
                        log.message or "",
                        log.traceback or "",
                        context_str,
                        created_at_str
                    ]
                )

            from flask import Response

            # 生成文件名
            timestamp = now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_export_{timestamp}.csv"

            return Response(
                output.getvalue(),
                mimetype="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}",
                    "Content-Type": "text/csv; charset=utf-8"
                },
            )

        return error_response("Unsupported export format", 400)

    except Exception as e:
        log_error(
            "Failed to export logs", 
            module="unified_logs", 
            format_type=format_type,
            level=level,
            module_filter=module,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            exception=e
        )
        return error_response("Failed to export logs", 500)


@unified_logs_bp.route("/api/cleanup", methods=["POST"])
@login_required
def cleanup_logs():
    """清理旧日志API"""
    try:
        # 检查权限（仅管理员）
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            return error_response("Permission denied", 403)

        days = int(request.json.get("days", 90))

        deleted_count = UnifiedLog.cleanup_old_logs(days=days)

        log_info(
            "Logs cleanup completed",
            module="unified_logs",
            deleted_count=deleted_count,
            days=days,
        )

        return success_response(
            {
                "deleted_count": deleted_count,
                "message": f"Successfully deleted {deleted_count} log entries older than {days} days",
            }
        )

    except Exception as e:
        log_error("Failed to cleanup logs", module="unified_logs", error=str(e))
        return error_response("Failed to cleanup logs", 500)


@unified_logs_bp.route("/api/real-time", methods=["GET"])
@login_required
def get_recent_logs():
    """获取实时日志API（用于实时监控）"""
    try:
        limit = int(request.args.get("limit", 20))
        level = request.args.get("level")

        query = UnifiedLog.query

        if level:
            try:
                log_level = LogLevel(level.upper())
                query = query.filter(UnifiedLog.level == log_level)
            except ValueError:
                return error_response("Invalid log level", 400)

        # 获取最近的日志
        recent_logs = query.order_by(desc(UnifiedLog.timestamp)).limit(limit).all()

        logs = [log.to_dict() for log in recent_logs]

        return success_response({"logs": logs})

    except Exception as e:
        log_error("Failed to get recent logs", module="unified_logs", error=str(e))
        return error_response("Failed to get recent logs", 500)


@unified_logs_bp.route("/api/health", methods=["GET"])
@login_required
def get_log_health():
    """获取日志系统健康状态API"""
    try:
        # 获取最近1小时的统计
        stats = UnifiedLog.get_log_statistics(hours=1)

        # 计算健康分数
        health_score = 100
        if stats["error_count"] > 0:
            health_score -= min(stats["error_count"] * 10, 50)

        if stats["error_rate"] > 10:
            health_score -= 20

        # 确定健康状态
        if health_score >= 90:
            status = "healthy"
        elif health_score >= 70:
            status = "warning"
        else:
            status = "critical"

        health_data = {
            "status": status,
            "health_score": health_score,
            "error_count": stats["error_count"],
            "error_rate": stats["error_rate"],
            "total_logs": stats["total_logs"],
            "last_updated": now().isoformat(),
        }

        return success_response(health_data)

    except Exception as e:
        log_error("Failed to get log health", module="unified_logs", error=str(e))
        return error_response("Failed to get log health", 500)


@unified_logs_bp.route("/api/stats", methods=["GET"])
@login_required
def get_log_stats():
    """获取日志统计信息API"""
    try:
        hours = int(request.args.get("hours", 24))
        
        # 计算时间范围
        start_time = now() - timedelta(hours=hours)
        
        # 总日志数
        total_logs = UnifiedLog.query.filter(UnifiedLog.timestamp >= start_time).count()
        
        # 错误日志数
        error_logs = UnifiedLog.query.filter(
            UnifiedLog.timestamp >= start_time,
            UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL])
        ).count()
        
        # 警告日志数
        warning_logs = UnifiedLog.query.filter(
            UnifiedLog.timestamp >= start_time,
            UnifiedLog.level == LogLevel.WARNING
        ).count()
        
        # 活跃模块数
        from sqlalchemy import distinct
        modules_count = db.session.query(distinct(UnifiedLog.module)).filter(
            UnifiedLog.timestamp >= start_time
        ).count()
        
        stats = {
            "total_logs": total_logs,
            "error_logs": error_logs,
            "warning_logs": warning_logs,
            "modules_count": modules_count,
            "time_range_hours": hours
        }
        
        return success_response(stats)
        
    except Exception as e:
        log_error("Failed to get log stats", module="unified_logs", error=str(e))
        return error_response("Failed to get log stats", 500)


@unified_logs_bp.route("/api/detail/<int:log_id>", methods=["GET"])
@login_required
def get_log_detail(log_id):
    """获取日志详情API"""
    try:
        log = UnifiedLog.query.get_or_404(log_id)
        
        return success_response({"log": log.to_dict()})
        
    except Exception as e:
        log_error("Failed to get log detail", module="unified_logs", error=str(e), log_id=log_id)
        return error_response("Failed to get log detail", 500)


