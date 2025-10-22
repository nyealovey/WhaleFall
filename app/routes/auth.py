
"""
鲸落 - 用户认证路由
"""

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.constants.system_constants import ErrorMessages, SuccessMessages
from app.errors import (
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    NotFoundError,
    ValidationError as AppValidationError,
)
from app.models.user import User
from app.utils.decorators import require_csrf
from app.utils.rate_limiter import login_rate_limit, password_reset_rate_limit
from app.utils.data_validator import validate_password
from app.utils.response_utils import jsonify_unified_error_message, jsonify_unified_success
from app.utils.structlog_config import get_auth_logger

# 创建蓝图
auth_bp = Blueprint("auth", __name__)

# 获取认证日志记录器
auth_logger = get_auth_logger()


@auth_bp.route("/api/login", methods=["POST"])
@require_csrf
@login_rate_limit
def login_api() -> "Response":
    """用户登录API"""
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
            "API登录失败：用户名或密码为空",
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
                user_agent=request.headers.get("User-Agent"),
            )

            # API登录，返回JWT token
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
            "API登录失败：用户账户已禁用",
            username=username,
            ip_address=request.remote_addr,
        )
        raise AuthorizationError(
            message=ErrorMessages.ACCOUNT_DISABLED,
            message_key="ACCOUNT_DISABLED",
        )

    auth_logger.warning(
        "API登录失败：用户名或密码错误",
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
    """用户登录页面"""
    if request.method == "POST":
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
                "页面登录失败：用户名或密码为空",
                username=username,
                ip_address=request.remote_addr,
            )
            flash("用户名和密码不能为空", "error")
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
                    user_agent=request.headers.get("User-Agent"),
                )

                # 页面登录，重定向到首页
                flash("登录成功！", "success")
                next_page = request.args.get("next")
                return redirect(next_page) if next_page else redirect(url_for("dashboard.index"))
            auth_logger.warning(
                "页面登录失败：账户已被禁用",
                username=username,
                user_id=user.id,
                ip_address=request.remote_addr,
            )
            flash("账户已被禁用", "error")
        else:
            auth_logger.warning(
                "页面登录失败：用户名或密码错误",
                username=username,
                ip_address=request.remote_addr,
            )
            flash("用户名或密码错误", "error")

    # GET请求，显示登录页面

    return render_template("auth/login.html")


@auth_bp.route("/api/logout", methods=["GET", "POST"])
@login_required
@require_csrf
def logout() -> "Response":
    """用户登出"""
    # 记录登出日志
    auth_logger.info(
        "用户登出",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.remote_addr,
        user_agent=request.headers.get("User-Agent"),
    )

    logout_user()

    if request.is_json:
        return jsonify_unified_success(message=SuccessMessages.LOGOUT_SUCCESS)

    flash("已成功登出", "info")
    return redirect(url_for("auth.login"))


# 注册功能已移除


@auth_bp.route("/profile")
@login_required
def profile() -> "str | Response":
    """用户资料页面"""
    if request.is_json:
        return jsonify_unified_success(
            data={
                "id": current_user.id,
                "username": current_user.username,
                "email": current_user.email,
                "role": current_user.role,
                "is_active": current_user.is_active,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
            },
            message=SuccessMessages.OPERATION_SUCCESS,
        )

    return render_template("auth/profile.html", user=current_user)


@auth_bp.route("/api/change-password", methods=["POST"])
@login_required
@password_reset_rate_limit
@require_csrf
def change_password_api() -> "Response":
    """修改密码API"""
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    old_password = data.get("old_password")
    new_password = data.get("new_password")
    confirm_password = data.get("confirm_password")

    # 验证输入
    if not old_password or not new_password:
        raise AppValidationError(message="所有字段都不能为空")

    if new_password != confirm_password:
        raise AppValidationError(message="两次输入的新密码不一致")

    # 验证旧密码
    if not current_user.check_password(old_password):
        auth_logger.warning(
            "API修改密码失败：旧密码错误",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
        )
        raise AuthenticationError(message="旧密码错误")

    # 验证新密码强度
    password_error = validate_password(new_password)
    if password_error:
        raise AppValidationError(message=password_error)

    try:
        # 更新密码
        current_user.set_password(new_password)
        db.session.commit()
    except Exception as exc:  # pragma: no cover - 数据库异常
        db.session.rollback()
        auth_logger.error(
            "API修改密码失败",
            module="auth",
            user_id=current_user.id,
            username=current_user.username,
            ip_address=request.remote_addr,
            error=str(exc),
            exc_info=True,
        )
        raise DatabaseError(message="密码修改失败") from exc

    # 记录操作日志
    auth_logger.info(
        "用户API修改密码成功",
        module="auth",
        user_id=current_user.id,
        username=current_user.username,
        ip_address=request.remote_addr,
    )

    return jsonify_unified_success(message=SuccessMessages.PASSWORD_CHANGED)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
@password_reset_rate_limit
@require_csrf
def change_password() -> "str | Response":
    """修改密码页面"""
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # 验证输入
        if not old_password or not new_password:
            flash("所有字段都不能为空", "error")
            return render_template("auth/change_password.html")

        if new_password != confirm_password:
            flash("两次输入的新密码不一致", "error")
            return render_template("auth/change_password.html")

        # 验证旧密码
        if not current_user.check_password(old_password):
            flash("旧密码错误", "error")
            return render_template("auth/change_password.html")

        # 更新密码
        try:
            current_user.set_password(new_password)
            db.session.commit()

            flash("密码修改成功！", "success")
            return redirect(url_for("auth.profile"))

        except Exception:
            db.session.rollback()
            flash("密码修改失败，请重试", "error")

    # GET请求，显示修改密码页面

    return render_template("auth/change_password.html")


# API路由
@auth_bp.route("/api/csrf-token", methods=["GET"])
def get_csrf_token() -> "Response":
    """获取CSRF令牌"""
    from flask_wtf.csrf import generate_csrf
    return jsonify_unified_success(
        data={"csrf_token": generate_csrf()},
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@auth_bp.route("/api/refresh", methods=["POST"])
@require_csrf
@jwt_required(refresh=True)
def refresh() -> "Response":
    """刷新JWT token"""
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    return jsonify_unified_success(
        data={
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
        },
        message=SuccessMessages.OPERATION_SUCCESS,
    )


@auth_bp.route("/api/me")
@jwt_required()
def me() -> "Response":
    """获取当前用户信息"""
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
