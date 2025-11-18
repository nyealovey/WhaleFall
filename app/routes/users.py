
"""
鲸落 - 用户管理路由
"""

from flask import Blueprint, Response, flash, render_template, request
from flask_login import current_user, login_required

from app import db
from app.errors import ConflictError, ValidationError
from app.constants import FlashCategory, HttpStatus, UserRole
from app.models.user import User
from app.views.user_form_view import UserFormView
from app.services.users import UserFormService
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
_user_form_service = UserFormService()


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

        users = User.query.order_by(User.created_at.desc()).all()
        role_options = [
            {"value": role, "label": UserRole.get_display_name(role)}
            for role in UserRole.ALL
        ]
        log_info(
            "成功获取用户列表",
            module="users",
            user_id=current_user.id if current_user.is_authenticated else None,
            total=len(users),
        )

        return render_template("auth/list.html", users=users, role_options=role_options)

    except Exception as e:
        log_error(
            "加载用户管理页面失败",
            module="users",
            exception=e,
            user_id=current_user.id if current_user.is_authenticated else None,
        )
        flash(f"获取用户列表失败: {str(e)}", FlashCategory.ERROR)
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
    payload = request.get_json(silent=True) or {}

    log_info(
        "创建用户请求",
        module="users",
        user_id=current_user.id,
        request_data=payload,
    )

    result = _user_form_service.upsert(payload)
    if not result.success or not result.data:
        if result.message_key == UserFormService.MESSAGE_USERNAME_EXISTS:
            raise ConflictError(result.message or "用户名已存在")
        raise ValidationError(result.message or "用户创建失败")

    user = result.data

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
        status=HttpStatus.CREATED,
    )


@users_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
@update_required
@require_csrf
def api_update_user(user_id: int) -> tuple[Response, int]:
    """更新用户API"""
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}

    log_info(
        "更新用户请求",
        module="users",
        user_id=current_user.id,
        target_user_id=user_id,
        request_data=payload,
    )

    result = _user_form_service.upsert(payload, user)
    if not result.success or not result.data:
        if result.message_key == UserFormService.MESSAGE_USERNAME_EXISTS:
            raise ConflictError(result.message or "用户名已存在")
        raise ValidationError(result.message or "用户更新失败")

    user = result.data

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

    if user.role == UserRole.ADMIN:
        admin_count = User.query.filter_by(role=UserRole.ADMIN).count()
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


@users_bp.route("/api/users/stats")
@login_required
@view_required
def api_get_stats() -> tuple[Response, int]:
    """获取用户统计信息API"""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(role=UserRole.ADMIN).count()
    user_users = User.query.filter_by(role=UserRole.USER).count()

    data = {
        "total": total_users,
        "active": active_users,
        "inactive": total_users - active_users,
        "admin": admin_users,
        "user": user_users,
    }

    return jsonify_unified_success(data=data)


# ---------------------------------------------------------------------------
# 表单路由
# ---------------------------------------------------------------------------
_user_create_view = UserFormView.as_view("user_create_form")
_user_create_view = login_required(create_required(require_csrf(_user_create_view)))

users_bp.add_url_rule(
    "/create",
    view_func=_user_create_view,
    methods=["GET", "POST"],
    defaults={"resource_id": None},
    endpoint="create",
)

_user_edit_view = UserFormView.as_view("user_edit_form")
_user_edit_view = login_required(update_required(require_csrf(_user_edit_view)))

users_bp.add_url_rule(
    "/<int:user_id>/edit",
    view_func=_user_edit_view,
    methods=["GET", "POST"],
    endpoint="edit",
)
