
"""鲸落 - 统一日志系统API路由
提供日志查询、展示和管理的RESTful API.
"""

from datetime import datetime, timedelta

from flask import Blueprint, Response, render_template, request
from flask_login import login_required
from sqlalchemy import Text, asc, cast, desc, or_

from app import db
from app.constants import LOG_LEVELS, TIME_RANGES
from app.errors import SystemError, ValidationError
from app.models.unified_log import LogLevel, UnifiedLog
from app.utils.query_filter_utils import get_log_modules as load_log_modules
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info
from app.utils.time_utils import time_utils

# 创建蓝图
history_logs_bp = Blueprint("history_logs", __name__)
# 兼容旧版 /logs 前缀请求
logs_bp = Blueprint("logs", __name__)


@history_logs_bp.route("/")
@logs_bp.route("/")
@login_required
def logs_dashboard() -> str | tuple[dict, int]:
    """日志中心仪表板.

    渲染日志查询和展示页面,提供日志级别、模块和时间范围的筛选选项.

    Returns:
        渲染的日志仪表板 HTML 页面.

    Raises:
        SystemError: 当页面加载失败时抛出.

    """
    try:
        module_values = load_log_modules()
        module_options = [{"value": value, "label": value} for value in module_values]
        return render_template(
            "history/logs/logs.html",
            log_level_options=LOG_LEVELS,
            module_options=module_options,
            time_range_options=TIME_RANGES,
        )
    except Exception as e:
        log_error("日志仪表盘渲染失败", module="history_logs", error=str(e))
        msg = "日志仪表盘加载失败"
        raise SystemError(msg) from e


def _safe_int(value: str | None, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    """安全地将字符串转换为整数并裁剪到范围.

    Args:
        value: 原始字符串值.
        default: 转换失败时使用的默认值.
        minimum: 最小值.
        maximum: 可选最大值.

    Returns:
        int: 转换后的整数.

    """
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    if parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def _parse_iso_datetime(raw_value: str | None) -> datetime | None:
    """解析 ISO 格式时间字符串.

    Args:
        raw_value: ISO 格式字符串,可为 None.

    Returns:
        datetime | None: 解析成功返回 datetime,否则 None.

    """
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(raw_value)
    except ValueError:
        return None


@history_logs_bp.route("/api/search", methods=["GET"])
@logs_bp.route("/api/search", methods=["GET"])
@login_required
def search_logs() -> Response:
    """搜索日志 API.

    支持按日志级别、模块、关键词、时间范围等条件搜索日志.
    支持分页查询和排序.

    Query Parameters:
        page: 页码,默认 1.
        per_page: 每页数量,默认 50.
        level: 日志级别筛选.
        module: 模块筛选.
        q: 搜索关键词.
        start_time: 开始时间(ISO 格式).
        end_time: 结束时间(ISO 格式).
        hours: 最近 N 小时.

    Returns:
        包含日志列表和分页信息的 JSON 响应.

    Raises:
        ValidationError: 当参数验证失败时抛出.
        SystemError: 当查询失败时抛出.

    """
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        level = request.args.get("level")
        module = request.args.get("module")
        search_term = request.args.get("q", "").strip()
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        hours = request.args.get("hours")  # 添加hours参数处理
        sort_by = request.args.get("sort_by", "timestamp")
        sort_order = request.args.get("sort_order", "desc")

        # 构建查询
        query = UnifiedLog.query

        # 时间范围过滤
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                query = query.filter(UnifiedLog.timestamp >= start_dt)
            except ValueError as exc:
                msg = "start_time 参数格式无效"
                raise ValidationError(msg) from exc

        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
                query = query.filter(UnifiedLog.timestamp <= end_dt)
            except ValueError as exc:
                msg = "end_time 参数格式无效"
                raise ValidationError(msg) from exc

        # hours参数优先级高于默认时间范围
        if hours and not start_time and not end_time:
            try:
                hours_int = int(hours)
                start_time_from_hours = time_utils.now() - timedelta(hours=hours_int)
                query = query.filter(UnifiedLog.timestamp >= start_time_from_hours)
            except ValueError as exc:
                msg = "hours 参数格式无效"
                raise ValidationError(msg) from exc
        elif not start_time and not end_time and not hours:
            default_start = time_utils.now() - timedelta(hours=24)
            query = query.filter(UnifiedLog.timestamp >= default_start)

        # 级别过滤
        if level:
            try:
                log_level = LogLevel(level.upper())
                query = query.filter(UnifiedLog.level == log_level)
            except ValueError as exc:
                msg = "日志级别参数无效"
                raise ValidationError(msg) from exc

        # 模块过滤
        if module:
            query = query.filter(UnifiedLog.module.like(f"%{module}%"))

        # 关键词搜索
        if search_term:
            search_filter = or_(
                UnifiedLog.message.like(f"%{search_term}%"),
                cast(UnifiedLog.context, Text).like(f"%{search_term}%"),
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

        query = query.order_by(asc(order_column)) if sort_order == "asc" else query.order_by(desc(order_column))

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

        return jsonify_unified_success(data=response_data)

    except Exception as e:
        log_error("日志查询失败", module="history_logs", error=str(e))
        msg = "日志查询失败"
        raise SystemError(msg) from e


@history_logs_bp.route("/api/list", methods=["GET"])
@logs_bp.route("/api/list", methods=["GET"])
@login_required
def list_logs() -> Response:
    """Grid.js 日志列表 API.

    Returns:
        Response: 包含分页日志数据的 JSON.

    Raises:
        ValidationError: 参数校验失败时抛出.
        SystemError: 查询或序列化失败时抛出.

    """
    try:
        page = _safe_int(request.args.get("page"), default=1, minimum=1)
        limit = _safe_int(request.args.get("limit"), default=50, minimum=1, maximum=200)
        sort_field = (request.args.get("sort") or "timestamp").lower()
        sort_order = (request.args.get("order") or "desc").lower()

        level_value = request.args.get("level")
        module_value = request.args.get("module")
        search_term = (request.args.get("search") or request.args.get("q") or "").strip()
        hours_param = request.args.get("hours")
        start_time_param = request.args.get("start_time")
        end_time_param = request.args.get("end_time")

        query = UnifiedLog.query

        start_dt = _parse_iso_datetime(start_time_param)
        end_dt = _parse_iso_datetime(end_time_param)

        if start_dt:
            query = query.filter(UnifiedLog.timestamp >= start_dt)
        if end_dt:
            query = query.filter(UnifiedLog.timestamp <= end_dt)

        if not start_dt and not end_dt:
            hours_value = _safe_int(hours_param, default=24, minimum=1, maximum=24 * 90)
            start_time = time_utils.now() - timedelta(hours=hours_value)
            query = query.filter(UnifiedLog.timestamp >= start_time)

        if level_value:
            try:
                log_level = LogLevel(level_value.upper())
                query = query.filter(UnifiedLog.level == log_level)
            except ValueError as exc:
                msg = "日志级别参数无效"
                raise ValidationError(msg) from exc

        if module_value:
            query = query.filter(UnifiedLog.module.like(f"%{module_value}%"))

        if search_term:
            query = query.filter(
                or_(
                    UnifiedLog.message.like(f"%{search_term}%"),
                    cast(UnifiedLog.context, Text).like(f"%{search_term}%"),
                ),
            )

        sortable_fields = {
            "id": UnifiedLog.id,
            "timestamp": UnifiedLog.timestamp,
            "level": UnifiedLog.level,
            "module": UnifiedLog.module,
            "message": UnifiedLog.message,
        }
        order_column = sortable_fields.get(sort_field, UnifiedLog.timestamp)
        query = query.order_by(asc(order_column)) if sort_order == "asc" else query.order_by(desc(order_column))

        pagination = query.paginate(page=page, per_page=limit, error_out=False)

        items: list[dict[str, object]] = []
        for log_entry in pagination.items:
            china_timestamp = time_utils.to_china(log_entry.timestamp) if log_entry.timestamp else None
            timestamp_display = (
                time_utils.format_china_time(china_timestamp, "%Y-%m-%d %H:%M:%S")
                if china_timestamp
                else "-"
            )
            items.append(
                {
                    "id": log_entry.id,
                    "timestamp": china_timestamp.isoformat() if china_timestamp else None,
                    "timestamp_display": timestamp_display,
                    "level": log_entry.level.value if log_entry.level else None,
                    "module": log_entry.module,
                    "message": log_entry.message,
                    "traceback": log_entry.traceback,
                    "context": log_entry.context,
                },
            )

        payload = {
            "items": items,
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "limit": pagination.per_page,
        }

        return jsonify_unified_success(data=payload, message="日志列表获取成功")

    except ValidationError:
        raise
    except Exception as error:
        log_error("获取日志列表失败", module="history_logs", error=str(error))
        msg = "获取日志列表失败"
        raise SystemError(msg) from error


@history_logs_bp.route("/api/statistics", methods=["GET"])
@logs_bp.route("/api/statistics", methods=["GET"])
@login_required
def get_log_statistics() -> Response:
    """获取日志统计信息 API.

    Returns:
        Response: 日志统计 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """
    try:
        hours = int(request.args.get("hours", 24))

        stats = UnifiedLog.get_log_statistics(hours=hours)

        log_info(
            "日志统计数据已获取",
            module="history_logs",
            hours=hours,
            total_logs=stats["total_logs"],
        )

        return jsonify_unified_success(data=stats)

    except Exception as e:
        log_error("获取日志统计失败", module="history_logs", error=str(e))
        msg = "获取日志统计失败"
        raise SystemError(msg) from e



@history_logs_bp.route("/api/modules", methods=["GET"])
@logs_bp.route("/api/modules", methods=["GET"])
@login_required
def list_log_modules() -> Response:
    """获取日志模块列表 API.

    Returns:
        Response: 模块列表 JSON.

    Raises:
        SystemError: 查询失败时抛出.

    """
    try:
        from sqlalchemy import distinct

        # 获取所有模块
        modules = db.session.query(distinct(UnifiedLog.module).label("module")).order_by(UnifiedLog.module).all()

        module_list = [module.module for module in modules]

        return jsonify_unified_success(data={"modules": module_list})

    except Exception as e:
        log_error("获取日志模块失败", module="history_logs", error=str(e))
        msg = "获取日志模块失败"
        raise SystemError(msg) from e


@history_logs_bp.route("/api/stats", methods=["GET"])
@logs_bp.route("/api/stats", methods=["GET"])
@login_required
def get_log_stats() -> tuple[dict, int]:
    """获取日志统计 API(兼容旧前端).

    Returns:
        tuple[dict, int]: 统一成功 JSON 与状态码.

    Raises:
        ValidationError: 参数格式错误时抛出.
        SystemError: 查询失败时抛出.

    """
    try:
        # 获取筛选参数
        hours = request.args.get("hours")
        level = request.args.get("level")
        module = request.args.get("module")
        q = request.args.get("q")

        # 构建基础查询
        query = UnifiedLog.query

        # 时间范围筛选
        if hours:
            try:
                hours_int = int(hours)
            except ValueError as exc:
                msg = "hours 参数格式无效"
                raise ValidationError(msg) from exc
            start_time = time_utils.now() - timedelta(hours=hours_int)
            query = query.filter(UnifiedLog.timestamp >= start_time)

        # 日志级别筛选
        if level:
            query = query.filter(UnifiedLog.level == level)

        # 模块筛选
        if module:
            query = query.filter(UnifiedLog.module == module)

        # 关键词搜索
        if q:
            query = query.filter(
                or_(
                    UnifiedLog.message.contains(q),
                    UnifiedLog.module.contains(q),
                ),
            )

        # 总日志数
        total_logs = query.count()

        error_query = query.filter(UnifiedLog.level.in_([LogLevel.ERROR, LogLevel.CRITICAL]))
        error_logs = error_query.count()

        # 警告日志数
        warning_query = query.filter(UnifiedLog.level == LogLevel.WARNING)
        warning_logs = warning_query.count()

        # 活跃模块数
        from sqlalchemy import distinct
        modules_query = db.session.query(distinct(UnifiedLog.module))

        # 应用相同的筛选条件到模块查询
        if hours:
            modules_query = modules_query.filter(UnifiedLog.timestamp >= start_time)
        if level:
            modules_query = modules_query.filter(UnifiedLog.level == level)
        if module:
            modules_query = modules_query.filter(UnifiedLog.module == module)
        if q:
            modules_query = modules_query.filter(
                or_(
                    UnifiedLog.message.contains(q),
                    UnifiedLog.module.contains(q),
                ),
            )

        modules_count = modules_query.count()

        stats = {
            "total_logs": total_logs,
            "error_logs": error_logs,
            "warning_logs": warning_logs,
            "modules_count": modules_count,
            "time_range_hours": int(hours) if hours else None,
        }

        return jsonify_unified_success(data=stats)

    except Exception as e:
        log_error("获取日志概要失败", module="history_logs", error=str(e))
        msg = "获取日志概要失败"
        raise SystemError(msg) from e


@history_logs_bp.route("/api/detail/<int:log_id>", methods=["GET"])
@logs_bp.route("/api/detail/<int:log_id>", methods=["GET"])
@login_required
def get_log_detail(log_id: int) -> tuple[dict, int]:
    """获取日志详情 API.

    Args:
        log_id: 日志记录 ID.

    Returns:
        tuple[dict, int]: 日志详情 JSON 与状态码.

    Raises:
        SystemError: 查询失败时抛出.

    """
    try:
        log = UnifiedLog.query.get_or_404(log_id)

        return jsonify_unified_success(data={"log": log.to_dict()})

    except Exception as e:
        log_error("获取日志详情失败", module="history_logs", error=str(e), log_id=log_id)
        msg = "获取日志详情失败"
        raise SystemError(msg) from e
