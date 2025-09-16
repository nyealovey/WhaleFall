"""
泰摸鱼吧 - 主要路由
"""

import psutil
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import login_required

from app.utils.decorators import admin_required
from app.utils.structlog_config import log_info
from app.utils.timezone import get_china_time

# 创建蓝图
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index() -> str:
    """首页 - 重定向到登录页面"""
    return redirect(url_for("auth.login"))


@main_bp.route("/favicon.ico")
def favicon() -> "Response":
    """提供favicon.ico文件"""
    # 返回一个空的响应，避免404错误
    return "", 204


@main_bp.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools() -> "Response":
    """处理Chrome开发者工具的请求"""
    # 返回一个空的响应，避免404错误
    return "", 204


@main_bp.route("/admin")
@login_required
@admin_required
def admin() -> str:
    """系统管理页面"""
    return render_template("admin/management.html")


@main_bp.route("/api/health")
def api_health() -> "Response":
    """健康检查"""
    import time

    start_time = time.time()
    from app import db

    # 检查数据库状态
    db_status = "connected"
    try:
        from sqlalchemy import text

        db.session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # 检查Redis状态
    redis_status = "connected"
    try:
        from flask import current_app

        redis_client = getattr(current_app, "redis_client", None)
        if redis_client:
            redis_client.ping()
        else:
            redis_status = "error"
    except Exception:
        redis_status = "error"

    # 整体状态
    overall_status = "healthy" if db_status == "connected" and redis_status == "connected" else "unhealthy"

    result = {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status,
        "timestamp": get_china_time().isoformat(),
        "uptime": get_system_uptime(),
    }

    # 记录API调用
    import time

    duration = (time.time() - start_time) * 1000
    log_info(
        "健康检查API调用",
        module="main",
        ip_address=request.remote_addr,
        duration_ms=duration,
    )

    return jsonify(result)


def get_system_uptime() -> "str | None":
    """获取系统运行时间"""
    try:
        from datetime import datetime

        uptime_seconds = psutil.boot_time()
        uptime = get_china_time() - datetime.fromtimestamp(uptime_seconds)

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        return f"{days}天 {hours}小时 {minutes}分钟"
    except Exception:
        return "未知"
