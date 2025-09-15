"""
泰摸鱼吧 - 系统日志管理路由
提供传统的系统日志查看功能
"""

from datetime import datetime, timedelta

from flask import Blueprint, Response, render_template, request
from flask_login import login_required  # type: ignore

from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.api_response import error_response, success_response
from app.utils.decorators import view_required
from app.utils.structlog_config import get_system_logger
from app.utils.timezone import now, utc_to_china

# 创建蓝图
system_logs_bp = Blueprint("system_logs", __name__)

# 获取系统日志记录器
system_logger = get_system_logger()


@system_logs_bp.route("/")
@login_required  # type: ignore
@view_required  # type: ignore
def index() -> str:
    """系统日志首页"""
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

        # 记录访问日志
        system_logger.info(
            "系统日志页面访问",
            module="system_logs",
            user_id=request.user.id if hasattr(request, 'user') else None,
            page=page,
            per_page=per_page,
            level=level,
            module_filter=module,
            search_term=q,
            hours=hours
        )

        return render_template("logs/system_logs.html", logs=logs)

    except Exception as e:
        system_logger.error(
            "系统日志页面访问失败",
            module="system_logs",
            error=str(e),
            exc_info=True
        )
        return render_template("errors/500.html", error=str(e)), 500


@system_logs_bp.route("/api/search", methods=["GET"])
@login_required  # type: ignore
def search_logs() -> Response:
    """搜索系统日志API"""
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
            query = query.filter(UnifiedLog.message.contains(search_term))

        # 排序
        if sort_by == "timestamp":
            if sort_order == "asc":
                query = query.order_by(UnifiedLog.timestamp.asc())
            else:
                query = query.order_by(UnifiedLog.timestamp.desc())
        elif sort_by == "level":
            if sort_order == "asc":
                query = query.order_by(UnifiedLog.level.asc())
            else:
                query = query.order_by(UnifiedLog.level.desc())

        # 分页查询
        logs_pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # 转换为字典格式
        logs = [log.to_dict() for log in logs_pagination.items]

        # 构建分页信息
        pagination = {
            "page": logs_pagination.page,
            "pages": logs_pagination.pages,
            "per_page": logs_pagination.per_page,
            "total": logs_pagination.total,
            "has_prev": logs_pagination.has_prev,
            "has_next": logs_pagination.has_next,
            "prev_num": logs_pagination.prev_num,
            "next_num": logs_pagination.next_num,
        }

        # 记录搜索日志
        system_logger.info(
            "系统日志搜索",
            module="system_logs",
            search_term=search_term,
            level=level,
            module_filter=module,
            page=page,
            per_page=per_page,
            results_count=len(logs)
        )

        return success_response({
            "logs": logs,
            "pagination": pagination
        })

    except Exception as e:
        system_logger.error(
            "系统日志搜索失败",
            module="system_logs",
            error=str(e),
            exc_info=True
        )
        return error_response("搜索日志失败", 500)


@system_logs_bp.route("/api/stats", methods=["GET"])
@login_required  # type: ignore
def get_log_stats() -> Response:
    """获取系统日志统计信息API"""
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
        
        # 信息日志数
        info_logs = UnifiedLog.query.filter(
            UnifiedLog.timestamp >= start_time,
            UnifiedLog.level == LogLevel.INFO
        ).count()
        
        # 调试日志数
        debug_logs = UnifiedLog.query.filter(
            UnifiedLog.timestamp >= start_time,
            UnifiedLog.level == LogLevel.DEBUG
        ).count()
        
        stats = {
            "total_logs": total_logs,
            "error_logs": error_logs,
            "warning_logs": warning_logs,
            "info_logs": info_logs,
            "debug_logs": debug_logs,
            "time_range_hours": hours
        }
        
        system_logger.info(
            "系统日志统计查询",
            module="system_logs",
            **stats
        )
        
        return success_response(stats)
        
    except Exception as e:
        system_logger.error(
            "系统日志统计查询失败",
            module="system_logs",
            error=str(e),
            exc_info=True
        )
        return error_response("获取统计信息失败", 500)


@system_logs_bp.route("/api/export", methods=["GET"])
@login_required  # type: ignore
def export_logs() -> Response:
    """导出系统日志API"""
    try:
        format_type = request.args.get("format", "json")
        level = request.args.get("level")
        module = request.args.get("module")
        hours = int(request.args.get("hours", 24))
        
        # 构建查询
        query = UnifiedLog.query
        
        # 时间过滤
        start_time = now() - timedelta(hours=hours)
        query = query.filter(UnifiedLog.timestamp >= start_time)
        
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
        
        # 获取日志数据
        logs = query.order_by(UnifiedLog.timestamp.desc()).all()
        
        if format_type == "json":
            from flask import jsonify
            logs_data = [log.to_dict() for log in logs]
            return jsonify({
                "success": True,
                "data": logs_data,
                "export_time": now().isoformat(),
                "total_count": len(logs_data)
            })
        elif format_type == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # 写入CSV头部
            writer.writerow([
                "时间", "级别", "模块", "消息", "上下文", "堆栈追踪"
            ])
            
            # 写入数据
            for log in logs:
                writer.writerow([
                    utc_to_china(log.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
                    log.level.value,
                    log.module,
                    log.message,
                    str(log.context) if log.context else "",
                    log.traceback or ""
                ])
            
            output.seek(0)
            
            from flask import make_response
            response = make_response(output.getvalue())
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename=system_logs_{now().strftime('%Y%m%d_%H%M%S')}.csv"
            return response
        else:
            return error_response("Unsupported format", 400)
            
    except Exception as e:
        system_logger.error(
            "系统日志导出失败",
            module="system_logs",
            error=str(e),
            exc_info=True
        )
        return error_response("导出日志失败", 500)
