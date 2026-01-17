"""鲸落 - 用户认证路由."""

from collections.abc import Callable
from typing import cast

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user, login_required, login_user, logout_user

from app.core.constants import FlashCategory, HttpHeaders, HttpMethod
from app.infra.flask_typing import RouteCallable, RouteReturn
from app.infra.route_safety import safe_route_call
from app.services.auth.login_service import LoginService
from app.utils.decorators import require_csrf
from app.utils.rate_limiter import login_rate_limit, password_reset_rate_limit
from app.utils.redirect_safety import resolve_safe_redirect_target
from app.utils.structlog_config import get_auth_logger
from app.views.password_forms import ChangePasswordFormView

# 创建蓝图
auth_bp = Blueprint("auth", __name__)

_change_password_view = cast(
    Callable[..., ResponseReturnValue],
    ChangePasswordFormView.as_view("auth_change_password_form"),
)
_change_password_view = login_required(password_reset_rate_limit()(require_csrf(_change_password_view)))
_change_password_view = cast(RouteCallable, _change_password_view)
auth_bp.add_url_rule(
    "/change-password",
    view_func=_change_password_view,
    methods=["GET", "POST"],
    endpoint="change_password",
)

# 获取认证日志记录器
auth_logger = get_auth_logger()


def login() -> RouteReturn:
    """用户登录页面.

    GET 请求渲染登录页面,POST 请求处理登录逻辑.

    Returns:
        GET: 渲染的登录页面.
        POST: 成功时重定向到首页,失败时重新渲染登录页面.

    Query Parameters:
        next: 登录成功后的重定向地址,可选.

    """

    def _execute() -> RouteReturn:
        if request.method == HttpMethod.POST:
            auth_logger.info(
                "收到登录请求",
                method=request.method,
                content_type=request.content_type,
                is_json=request.is_json,
                ip_address=request.remote_addr,
            )

            username = request.form.get("username")
            password = request.form.get("password")
            remember = bool(request.form.get("remember"))

            if not username or not password:
                auth_logger.warning(
                    "页面登录失败:用户名或密码为空",
                    username=username,
                    ip_address=request.remote_addr,
                )
                flash("用户名和密码不能为空", FlashCategory.ERROR)
                return render_template("auth/login.html")

            user = LoginService.authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login_user(user, remember=remember)

                    auth_logger.info(
                        "用户页面登录成功",
                        module="auth",
                        user_id=user.id,
                        username=user.username,
                        ip_address=request.remote_addr,
                        user_agent=request.headers.get(HttpHeaders.USER_AGENT),
                    )

                    flash("登录成功!", FlashCategory.SUCCESS)
                    next_page = resolve_safe_redirect_target(
                        request.args.get("next"),
                        fallback=url_for("dashboard.index"),
                    )
                    return redirect(next_page)

                auth_logger.warning(
                    "页面登录失败:账户已被停用",
                    username=username,
                    user_id=user.id,
                    ip_address=request.remote_addr,
                )
                flash("账户已被停用", FlashCategory.ERROR)
            else:
                auth_logger.warning(
                    "页面登录失败:用户名或密码错误",
                    username=username,
                    ip_address=request.remote_addr,
                )
                flash("用户名或密码错误", FlashCategory.ERROR)

        return render_template("auth/login.html")

    return safe_route_call(
        _execute,
        module="auth",
        action="login",
        public_error="登录失败,请稍后重试",
        context={"method": request.method},
        include_actor=False,
    )


auth_bp.add_url_rule(
    "/login",
    view_func=cast(RouteCallable, login_rate_limit()(require_csrf(login))),
    methods=["GET", "POST"],
)


def logout() -> RouteReturn:
    """用户登出.

    清除用户会话并重定向到登录页面.

    Returns:
        重定向到登录页面.

    """

    def _execute() -> RouteReturn:
        auth_logger.info(
            "用户登出",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.headers.get(HttpHeaders.USER_AGENT),
        )

        logout_user()

        flash("已成功登出", FlashCategory.INFO)
        return redirect(url_for("auth.login"))

    return safe_route_call(
        _execute,
        module="auth",
        action="logout",
        public_error="登出失败,请稍后重试",
    )


auth_bp.add_url_rule(
    "/logout",
    view_func=cast(RouteCallable, login_required(require_csrf(logout))),
    methods=["POST"],
)


# legacy `*/api/*` JSON API 已迁移到 `/api/v1/**`, 旧路径不再提供路由.
