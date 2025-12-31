"""鲸落 - 主要路由."""

from http import HTTPStatus
from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, request, send_from_directory, url_for

from app.types import RouteReturn

# 创建蓝图
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index() -> RouteReturn:
    """首页 - 重定向到登录页面.

    Returns:
        重定向响应到登录页面.

    """
    return redirect(url_for("auth.login"))


@main_bp.route("/about")
def about() -> RouteReturn:
    """关于页面.

    Returns:
        str: 关于页面模板.

    """
    return render_template("about.html")


@main_bp.route("/favicon.ico")
def favicon() -> RouteReturn:
    """提供 favicon.ico 文件,避免 404.

    Returns:
        Response: 空响应,状态码 204.

    """
    # 返回一个空的响应,避免404错误
    return "", HTTPStatus.NO_CONTENT


@main_bp.route("/apple-touch-icon.png")
@main_bp.route("/apple-touch-icon-precomposed.png")
def apple_touch_icon() -> RouteReturn:
    """提供 Apple Touch Icon,避免移动端 404.

    Returns:
        Response: 发送图标文件.

    """
    icon_name = "apple-touch-icon-precomposed.png" if "precomposed" in request.path else "apple-touch-icon.png"
    static_root = current_app.static_folder or str(Path(current_app.root_path) / "static")
    icon_path = Path(static_root) / "img"
    return send_from_directory(str(icon_path), icon_name)


@main_bp.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools() -> RouteReturn:
    """处理 Chrome DevTools 配置请求.

    Returns:
        Response: 空响应,状态码 204.

    """
    # 返回一个空的响应,避免404错误
    return "", HTTPStatus.NO_CONTENT


# Admin route removed - admin/management.html deleted
