"""鲸落 - 用户认证路由."""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.constants import FlashCategory, HttpHeaders, HttpMethod, TimeConstants
from app.constants.system_constants import ErrorMessages, SuccessMessages
from app.errors import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError as AppValidationError,
)
from app.models.user import User
from app.services.auth import ChangePasswordFormService
from app.utils.decorators import require_csrf
from app.utils.rate_limiter import login_rate_limit, password_reset_rate_limit
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import get_auth_logger
from app.views.password_forms import ChangePasswordFormView

# 创建蓝图
auth_bp = Blueprint("auth", __name__)
_change_password_service = ChangePasswordFormService()

_change_password_view = ChangePasswordFormView.as_view("auth_change_password_form")
_change_password_view = login_required(password_reset_rate_limit(require_csrf(_change_password_view)))
auth_bp.add_url_rule(
    "/change-password",
    view_func=_change_password_view,
    methods=["GET", "POST"],
    endpoint="change_password",
)

# 获取认证日志记录器
auth_logger = get_auth_logger()


@auth_bp.route("/api/login", methods=["POST"])
@require_csrf
@login_rate_limit
def authenticate_user() -> "Response":
    """用户登录 API.

    验证用户名和密码,成功后返回 JWT token.

    Returns:
        JSON 响应,包含 access_token、refresh_token 和用户信息.

    Raises:
        AppValidationError: 当用户名或密码为空时抛出.
        AuthorizationError: 当账户被禁用时抛出.
        AuthenticationError: 当用户名或密码错误时抛出.

    """
    # 添加调试日志
    auth_logger.info(
        "收到API登录请求",
        method=request.method,
        content_type=request.content_type,
        form_data=dict(request.form),
        is_json=request.is_json,
        ip_address=request.remote_addr,
    )
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    username = (data.get("username") or "").strip()
    password = data.get("password")

    if not username or not password:
        auth_logger.warning(
            "API登录失败:用户名或密码为空",
            username=username,
            ip_address=request.remote_addr,
        )
        raise AppValidationError(message="用户名和密码不能为空")

    # 查找用户
    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        if user.is_active:
            # 登录成功
            login_user(user, remember=True)

            # 记录登录日志
            auth_logger.info(
                "用户API登录成功",
                module="auth",
                user_id=user.id,
                username=user.username,
                ip_address=request.remote_addr,
                user_agent=request.headers.get(HttpHeaders.USER_AGENT),
            )

            # API登录,返回JWT token
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)

            return jsonify_unified_success(
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                        "is_active": user.is_active,
                    },
                },
                message=SuccessMessages.LOGIN_SUCCESS,
            )

        auth_logger.warning(
            "API登录失败:用户账户已禁用",
            username=username,
            ip_address=request.remote_addr,
        )
        raise AuthorizationError(
            message=ErrorMessages.ACCOUNT_DISABLED,
            message_key="ACCOUNT_DISABLED",
        )

    auth_logger.warning(
        "API登录失败:用户名或密码错误",
        username=username,
        ip_address=request.remote_addr,
    )
    raise AuthenticationError(
        message=ErrorMessages.INVALID_CREDENTIALS,
        message_key="INVALID_CREDENTIALS",
    )


@auth_bp.route("/login", methods=["GET", "POST"])
@login_rate_limit
@require_csrf
def login() -> "str | Response":
    """用户登录页面.

    GET 请求渲染登录页面,POST 请求处理登录逻辑.

    Returns:
        GET: 渲染的登录页面.
        POST: 成功时重定向到首页,失败时重新渲染登录页面.

    Query Parameters:
        next: 登录成功后的重定向地址,可选.

    """
    if request.method == HttpMethod.POST:
        # 添加调试日志
        auth_logger.info(
            "收到登录请求",
            method=request.method,
            content_type=request.content_type,
            form_data=dict(request.form),
            is_json=request.is_json,
            ip_address=request.remote_addr,
        )

        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            auth_logger.warning(
                "页面登录失败:用户名或密码为空",
                username=username,
                ip_address=request.remote_addr,
            )
            flash("用户名和密码不能为空", FlashCategory.ERROR)
            return render_template("auth/login.html")

        # 查找用户
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.is_active:
                # 登录成功
                login_user(user, remember=True)

                # 记录登录日志
                auth_logger.info(
                    "用户页面登录成功",
                    module="auth",
                    user_id=user.id,
                    username=user.username,
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get(HttpHeaders.USER_AGENT),
                )

                # 页面登录,重定向到首页
                flash("登录成功!", FlashCategory.SUCCESS)
                next_page = request.args.get("next")
                return redirect(next_page) if next_page else redirect(url_for("dashboard.index"))
            auth_logger.warning(
                "页面登录失败:账户已被禁用",
                username=username,
                user_id=user.id,
                ip_address=request.remote_addr,
            )
            flash("账户已被禁用", FlashCategory.ERROR)
        else:
            auth_logger.warning(
                "页面登录失败:用户名或密码错误",
                username=username,
                ip_address=request.remote_addr,
            )
            flash("用户名或密码错误", FlashCategory.ERROR)

    # GET请求,显示登录页面

    return render_template("auth/login.html")


@auth_bp.route("/api/logout", methods=["GET", "POST"])
@login_required
@require_csrf
def logout() -> "Response":
    """用户登出.

    清除用户会话并重定向到登录页面.

    Returns:
        JSON 响应或重定向到登录页面.

    """
    # 记录登出日志
    auth_logger.info(
        "用户登出",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.remote_addr,
        user_agent=request.headers.get(HttpHeaders.USER_AGENT),
    )

    logout_user()

    if request.is_json:
        return jsonify_unified_success(message=SuccessMessages.LOGOUT_SUCCESS)

    flash("已成功登出", FlashCategory.INFO)
    return redirect(url_for("auth.login"))


# 注册功能已移除


@auth_bp.route("/api/change-password", methods=["POST"])
@login_required
@password_reset_rate_limit
@require_csrf
def submit_change_password() -> "Response":
    """修改密码 API.

    验证旧密码并设置新密码.

    Returns:
        JSON 响应.

    Raises:
        AuthenticationError: 当旧密码错误时抛出.
        AppValidationError: 当表单验证失败时抛出.

    """
    payload = request.get_json(silent=True) if request.is_json else request.form
    payload = payload or {}

    result = _change_password_service.upsert(payload, current_user)
    if not result.success:
        auth_logger.warning(
            "API修改密码失败",
            module="auth",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            error=result.message,
        )
        if result.message_key == "INVALID_OLD_PASSWORD":
            raise AuthenticationError(message=result.message or "旧密码错误")
        raise AppValidationError(message=result.message or "密码修改失败")

    auth_logger.info(
        "用户API修改密码成功",
        module="auth",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.remote_addr,
    )

    return jsonify_unified_success(message=SuccessMessages.PASSWORD_CHANGED)


# API路由
@auth_bp.route("/api/csrf-token", methods=["GET"])
def get_csrf_token() -> "Response":
    """获取 CSRF 令牌.

    Returns:
        JSON 响应,包含 CSRF token.

    """
    from flask_wtf.csrf import generate_csrf

    return jsonify_unified_success(
        data={"csrf_token": generate_csrf()},
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@auth_bp.route("/api/refresh", methods=["POST"])
@require_csrf
@jwt_required(refresh=True)
def refresh() -> "Response":
    """刷新 JWT token.

    使用 refresh token 获取新的 access token.

    Returns:
        JSON 响应,包含新的 access_token.

    """
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    return jsonify_unified_success(
        data={
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": TimeConstants.ONE_HOUR,
        },
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@auth_bp.route("/api/me")
@jwt_required()
def me() -> "Response":
    """获取当前用户信息.

    通过 JWT token 获取当前登录用户的详细信息.

    Returns:
        JSON 响应,包含用户信息.

    Raises:
        NotFoundError: 当用户不存在时抛出.

    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        raise NotFoundError(message="用户不存在")

    return jsonify_unified_success(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        },
        message=SuccessMessages.OPERATION_SUCCESS,
    )
