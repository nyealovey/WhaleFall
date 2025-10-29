
"""
鲸落 - 主要路由
"""

from http import HTTPStatus

from flask import Blueprint, Response, redirect, render_template, url_for

from app.utils.response_utils import jsonify_unified_success

# 创建蓝图
main_bp = Blueprint("main", __name__)


@main_bp.route("/admin/api/app-info", methods=["GET"])
def app_info() -> tuple[Response, int]:
    """获取应用信息（供前端展示应用名称等）"""
    return jsonify_unified_success(data={"app_name": "鲸落", "app_version": "1.1.2"})


@main_bp.route("/")
def index() -> str:
    """首页 - 重定向到登录页面"""
    return redirect(url_for("auth.login"))


@main_bp.route("/about")
def about() -> str:
    """关于页面"""
    return render_template("about.html")


@main_bp.route("/favicon.ico")
def favicon() -> "Response":
    """提供favicon.ico文件"""
    # 返回一个空的响应，避免404错误
    return "", HTTPStatus.NO_CONTENT


@main_bp.route("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools() -> "Response":
    """处理Chrome开发者工具的请求"""
    # 返回一个空的响应，避免404错误
    return "", HTTPStatus.NO_CONTENT


# Admin route removed - admin/management.html deleted
