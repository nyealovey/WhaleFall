
"""
鲸落 - 用户管理路由
"""

import re

from flask import Blueprint, Response, flash, render_template, request
from flask_login import current_user, login_required

from app import db
from app.errors import ConflictError, ValidationError
from app.models.user import User
from app.utils.decorators import (
    create_required,
    delete_required,
    require_csrf,
    update_required,
    view_required,
)
from app.utils.response_utils import jsonify_unified_success
from app.utils.structlog_config import log_error, log_info

# 创建蓝图
users_bp = Blueprint("users", __name__)


@users_bp.route("/")
@login_required
@view_required
def index() -> str:
    """用户管理首页"""
    try:
        log_info(
            "加载用户管理页面",
            module="users",
            user_id=current_user.id if current_user.is_authenticated else None,
        )

        # 获取分页参数
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        log_info(
            "用户管理页面分页参数",
            module="users",
            user_id=current_user.id if current_user.is_authenticated else None,
            page=page,
            per_page=per_page,
        )

        # 分页查询
        users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        log_info(
            "成功获取用户列表",
            module="users",
            user_id=current_user.id if current_user.is_authenticated else None,
            total=users.total,
            page=users.page,
            per_page=users.per_page,
        )

        return render_template("auth/list.html", users=users)

    except Exception as e:
        log_error(
            "加载用户管理页面失败",
            module="users",
            exception=e,
            user_id=current_user.id if current_user.is_authenticated else None,
            page=request.args.get("page", type=int),
            per_page=request.args.get("per_page", type=int),
        )
        flash(f"获取用户列表失败: {str(e)}", "error")
        return render_template("auth/list.html", users=None, stats={})


@users_bp.route("/api/users")
@login_required
@view_required
def api_get_users() -> tuple[Response, int]:
    """获取用户列表API"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    search = request.args.get("search", "", type=str)
    role_filter = request.args.get("role", "", type=str)
    status_filter = request.args.get("status", "", type=str)

    query = User.query

    if search:
        query = query.filter(User.username.contains(search))

    if role_filter:
        query = query.filter(User.role == role_filter)

    if status_filter:
        if status_filter == "active":
            query = query.filter(User.is_active.is_(True))
        elif status_filter == "inactive":
            query = query.filter(User.is_active.is_(False))

    users_pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    users_data = [user.to_dict() for user in users_pagination.items]

    payload = {
        "users": users_data,
        "pagination": {
            "page": users_pagination.page,
            "pages": users_pagination.pages,
            "per_page": users_pagination.per_page,
            "total": users_pagination.total,
            "has_next": users_pagination.has_next,
            "has_prev": users_pagination.has_prev,
        },
    }
    return jsonify_unified_success(data=payload)


@users_bp.route("/api/users/<int:user_id>")
@login_required
@view_required
def api_get_user(user_id: int) -> tuple[Response, int]:
    """获取单个用户信息API"""
    user = User.query.get_or_404(user_id)
    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message="获取用户信息成功",
    )


@users_bp.route("/api/users", methods=["POST"])
@login_required
@create_required
@require_csrf
def api_create_user() -> tuple[Response, int]:
    """创建用户API"""
    data = request.get_json() or {}

    log_info(
        "创建用户请求",
        module="users",
        user_id=current_user.id,
        request_data=data,
    )

    required_fields = ["username", "password", "role"]
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"缺少必填字段: {field}")

    username = data["username"].strip()
    password = data["password"]
    role = data["role"]
    is_active = data.get("is_active", True)

    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        raise ValidationError("用户名只能包含字母、数字和下划线，长度3-20位")

    if User.query.filter_by(username=username).first():
        raise ConflictError("用户名已存在")

    if role not in ["admin", "user"]:
        raise ValidationError("角色只能是admin或user")

    try:
        user = User(username=username, password=password, role=role)
    except ValueError as exc:
        log_error(
            "创建用户失败: 密码不符合要求",
            module="users",
            user_id=current_user.id,
            error=str(exc),
        )
        raise ValidationError(f"密码不符合要求: {exc}") from exc

    user.is_active = is_active
    db.session.add(user)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "创建用户失败",
            module="users",
            user_id=current_user.id,
            error=str(exc),
        )
        raise

    log_info(
        "创建用户成功",
        module="users",
        user_id=current_user.id,
        created_user_id=user.id,
        created_username=user.username,
        created_role=user.role,
        is_active=user.is_active,
    )

    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message="用户创建成功",
        status=201,
    )


@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def api_update_user(user_id: int) -> tuple[Response, int]:
    """更新用户API"""
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}

    log_info(
        "更新用户请求",
        module="users",
        user_id=current_user.id,
        target_user_id=user_id,
        request_data=data,
    )

    if "username" in data:
        username = data["username"].strip()
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            raise ValidationError("用户名只能包含字母、数字和下划线，长度3-20位")

        existing_user = User.query.filter(User.username == username, User.id != user_id).first()
        if existing_user:
            raise ConflictError("用户名已存在")

        user.username = username

    if "password" in data and data["password"]:
        try:
            user.set_password(data["password"])
        except ValueError as exc:
            log_error(
                "更新用户失败: 密码不符合要求",
                module="users",
                user_id=current_user.id,
                target_user_id=user_id,
                error=str(exc),
            )
            raise ValidationError(f"密码不符合要求: {exc}") from exc

    if "role" in data:
        if data["role"] not in ["admin", "user"]:
            raise ValidationError("角色只能是admin或user")
        user.role = data["role"]

    if "is_active" in data:
        user.is_active = bool(data["is_active"])

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "更新用户失败",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(exc),
        )
        raise

    log_info(
        "更新用户",
        module="users",
        user_id=current_user.id,
        updated_user_id=user.id,
        updated_username=user.username,
        updated_role=user.role,
        is_active=user.is_active,
    )

    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message="用户更新成功",
    )


@users_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@delete_required
@require_csrf
def api_delete_user(user_id: int) -> tuple[Response, int]:
    """删除用户API"""
    user = User.query.get_or_404(user_id)

    deleted_username = user.username
    deleted_role = user.role

    if user.id == current_user.id:
        log_error(
            "删除用户失败: 不能删除自己的账户",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
        )
        raise ValidationError("不能删除自己的账户")

    if user.role == "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count <= 1:
            log_error(
                "删除用户失败: 不能删除最后一个管理员账户",
                module="users",
                user_id=current_user.id,
                target_user_id=user_id,
            )
            raise ValidationError("不能删除最后一个管理员账户")

    db.session.delete(user)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "删除用户失败",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(exc),
        )
        raise

    log_info(
        "删除用户",
        module="users",
        user_id=current_user.id,
        deleted_user_id=user_id,
        deleted_username=deleted_username,
        deleted_role=deleted_role,
    )

    return jsonify_unified_success(message="用户删除成功")


@users_bp.route("/api/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@update_required
@require_csrf
def api_toggle_user_status(user_id: int) -> tuple[Response, int]:
    """切换用户状态API"""
    user = User.query.get_or_404(user_id)

    old_status = user.is_active
    username = user.username
    role = user.role

    if user.id == current_user.id:
        log_error(
            "切换用户状态失败: 不能禁用自己的账户",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
        )
        raise ValidationError("不能禁用自己的账户")

    if user.role == "admin" and user.is_active:
        admin_count = User.query.filter_by(role="admin", is_active=True).count()
        if admin_count <= 1:
            log_error(
                "切换用户状态失败: 不能禁用最后一个管理员账户",
                module="users",
                user_id=current_user.id,
                target_user_id=user_id,
            )
            raise ValidationError("不能禁用最后一个管理员账户")

    user.is_active = not user.is_active
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log_error(
            "切换用户状态失败",
            module="users",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(exc),
        )
        raise

    status_text = "启用" if user.is_active else "禁用"
    log_info(
        f"切换用户状态: {status_text}",
        module="users",
        user_id=current_user.id,
        target_user_id=user_id,
        target_username=username,
        target_role=role,
        old_status=old_status,
        new_status=user.is_active,
    )

    return jsonify_unified_success(
        data={"user": user.to_dict()},
        message=f"用户{status_text}成功",
    )


@users_bp.route("/api/users/stats")
@login_required
@view_required
def api_get_stats() -> tuple[Response, int]:
    """获取用户统计信息API"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role="admin").count()
    user_users = User.query.filter_by(role="user").count()

    data = {
        "total": total_users,
        "active": active_users,
        "inactive": total_users - active_users,
        "admin": admin_users,
        "user": user_users,
    }

    return jsonify_unified_success(data=data)
