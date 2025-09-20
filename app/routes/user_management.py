"""
鲸落 - 用户管理路由
"""

import re

from flask import Blueprint, Response, flash, render_template, request
from flask_login import current_user, login_required

from app import db
from app.models.user import User
from app.utils.api_response import APIResponse
from app.utils.decorators import (
    create_required,
    delete_required,
    update_required,
    view_required,
)
from app.utils.structlog_config import log_error, log_info

# 创建蓝图


@user_management_bp.route("/")
@login_required
@view_required
def index() -> str:
    """用户管理首页"""
    try:
        # 获取分页参数
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)

        # 分页查询
        users = User.query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

        return render_template("user_management/management.html", users=users)

    except Exception as e:
        flash(f"获取用户列表失败: {str(e)}", "error")
        return render_template("user_management/management.html", users=None, stats={})


@user_management_bp.route("/api/users")
@login_required
@view_required
def api_get_users() -> "Response":
    """获取用户列表API"""
    try:
        # 获取分页参数
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 10, type=int)
        search = request.args.get("search", "", type=str)
        role_filter = request.args.get("role", "", type=str)
        status_filter = request.args.get("status", "", type=str)

        # 构建查询
        query = User.query

        # 搜索功能
        if search:
            query = query.filter(User.username.contains(search))

        # 角色筛选
        if role_filter:
            query = query.filter(User.role == role_filter)

        # 状态筛选
        if status_filter:
            if status_filter == "active":
                query = query.filter(User.is_active)
            elif status_filter == "inactive":
                query = query.filter(not User.is_active)

        # 分页查询
        users_pagination = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        # 转换为字典格式
        users_data = []
        for user in users_pagination.items:
            users_data.append(user.to_dict())

        return APIResponse.success(
            {
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
        )

    except Exception:
        return APIResponse.error("获取用户列表失败: {str(e)}")


@user_management_bp.route("/api/users", methods=["POST"])
@login_required
@create_required
def api_create_user() -> "Response":
    """创建用户API"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = ["username", "password", "role"]
        for field in required_fields:
            if not data.get(field):
                return APIResponse.error("缺少必填字段: {field}")

        username = data["username"].strip()
        password = data["password"]
        role = data["role"]
        is_active = data.get("is_active", True)

        # 验证用户名格式
        if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
            return APIResponse.error("用户名只能包含字母、数字和下划线，长度3-20位")

        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return APIResponse.error("用户名已存在")

        # 验证角色
        if role not in ["admin", "user"]:
            return APIResponse.error("角色只能是admin或user")

        # 创建用户
        user = User(username=username, password=password, role=role)
        user.is_active = is_active
        db.session.add(user)
        db.session.commit()

        # 记录操作成功日志
        log_info(
            "创建用户",
            module="user_management",
            user_id=current_user.id,
            created_user_id=user.id,
            created_username=user.username,
            created_role=user.role,
            is_active=user.is_active,
        )

        return APIResponse.success({"message": "用户创建成功", "user": user.to_dict()})

    except ValueError as e:
        log_error(
            "创建用户失败: 密码不符合要求",
            module="user_management",
            user_id=current_user.id,
            error=str(e),
        )
        return APIResponse.error("密码不符合要求: {str(e)}")
    except Exception as e:
        db.session.rollback()
        log_error(
            "创建用户失败",
            module="user_management",
            user_id=current_user.id,
            error=str(e),
        )
        return APIResponse.error("创建用户失败: {str(e)}")


@user_management_bp.route("/api/users/<int:user_id>", methods=["PUT"])
@login_required
@update_required
def api_update_user(user_id: int) -> "Response":
    """更新用户API"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()

        # 验证用户名格式
        if "username" in data:
            username = data["username"].strip()
            if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
                return APIResponse.error("用户名只能包含字母、数字和下划线，长度3-20位")

            # 检查用户名是否已被其他用户使用
            existing_user = User.query.filter(User.username == username, User.id != user_id).first()
            if existing_user:
                return APIResponse.error("用户名已存在")

            user.username = username

        # 更新密码
        if "password" in data and data["password"]:
            user.set_password(data["password"])

        # 更新角色
        if "role" in data:
            if data["role"] not in ["admin", "user"]:
                return APIResponse.error("角色只能是admin或user")
            user.role = data["role"]

        # 更新状态
        if "is_active" in data:
            user.is_active = bool(data["is_active"])

        db.session.commit()

        # 记录操作成功日志
        log_info(
            "更新用户",
            module="user_management",
            user_id=current_user.id,
            updated_user_id=user.id,
            updated_username=user.username,
            updated_role=user.role,
            is_active=user.is_active,
        )

        return APIResponse.success({"message": "用户更新成功", "user": user.to_dict()})

    except ValueError as e:
        log_error(
            "更新用户失败: 密码不符合要求",
            module="user_management",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(e),
        )
        return APIResponse.error("密码不符合要求: {str(e)}")
    except Exception as e:
        db.session.rollback()
        log_error(
            "更新用户失败",
            module="user_management",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(e),
        )
        return APIResponse.error("更新用户失败: {str(e)}")


@user_management_bp.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@delete_required
def api_delete_user(user_id: int) -> "Response":
    """删除用户API"""
    try:
        user = User.query.get_or_404(user_id)

        # 记录删除前的用户信息
        deleted_username = user.username
        deleted_role = user.role

        # 不能删除自己
        if user.id == current_user.id:
            log_error(
                "删除用户失败: 不能删除自己的账户",
                module="user_management",
                user_id=current_user.id,
                target_user_id=user_id,
            )
            return APIResponse.error("不能删除自己的账户")

        # 不能删除最后一个管理员
        if user.role == "admin":
            admin_count = User.query.filter_by(role="admin").count()
            if admin_count <= 1:
                log_error(
                    "删除用户失败: 不能删除最后一个管理员账户",
                    module="user_management",
                    user_id=current_user.id,
                    target_user_id=user_id,
                )
                return APIResponse.error("不能删除最后一个管理员账户")

        db.session.delete(user)
        db.session.commit()

        # 记录操作成功日志
        log_info(
            "删除用户",
            module="user_management",
            user_id=current_user.id,
            deleted_user_id=user_id,
            deleted_username=deleted_username,
            deleted_role=deleted_role,
        )

        return APIResponse.success({"message": "用户删除成功"})

    except Exception as e:
        db.session.rollback()
        log_error(
            "删除用户失败",
            module="user_management",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(e),
        )
        return APIResponse.error("删除用户失败: {str(e)}")


@user_management_bp.route("/api/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@update_required
def api_toggle_user_status(user_id: int) -> "Response":
    """切换用户状态API"""
    try:
        user = User.query.get_or_404(user_id)

        # 记录切换前的状态
        old_status = user.is_active
        username = user.username
        role = user.role

        # 不能禁用自己
        if user.id == current_user.id:
            log_error(
                "切换用户状态失败: 不能禁用自己的账户",
                module="user_management",
                user_id=current_user.id,
                target_user_id=user_id,
            )
            return APIResponse.error("不能禁用自己的账户")

        # 不能禁用最后一个管理员
        if user.role == "admin" and user.is_active:
            admin_count = User.query.filter_by(role="admin", is_active=True).count()
            if admin_count <= 1:
                log_error(
                    "切换用户状态失败: 不能禁用最后一个管理员账户",
                    module="user_management",
                    user_id=current_user.id,
                    target_user_id=user_id,
                )
                return APIResponse.error("不能禁用最后一个管理员账户")

        user.is_active = not user.is_active
        db.session.commit()

        # 记录操作成功日志
        status_text = "启用" if user.is_active else "禁用"
        log_info(
            f"切换用户状态: {status_text}",
            module="user_management",
            user_id=current_user.id,
            target_user_id=user_id,
            target_username=username,
            target_role=role,
            old_status=old_status,
            new_status=user.is_active,
        )

        return APIResponse.success({"message": f"用户{status_text}成功", "user": user.to_dict()})

    except Exception as e:
        db.session.rollback()
        log_error(
            "切换用户状态失败",
            module="user_management",
            user_id=current_user.id,
            target_user_id=user_id,
            error=str(e),
        )
        return APIResponse.error("切换用户状态失败: {str(e)}")


@user_management_bp.route("/api/users/stats")
@login_required
@view_required
def api_get_stats() -> "Response":
    """获取用户统计信息API"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admin_users = User.query.filter_by(role="admin").count()
        user_users = User.query.filter_by(role="user").count()

        return APIResponse.success(
            {
                "total": total_users,
                "active": active_users,
                "inactive": total_users - active_users,
                "admin": admin_users,
                "user": user_users,
            }
        )

    except Exception:
        return APIResponse.error("获取统计信息失败: {str(e)}")
