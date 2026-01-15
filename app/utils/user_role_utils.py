"""用户角色工具.

从 `app/core/constants/user_roles.py` 读取静态映射,提供权限判断/展示文案等纯函数.
"""

from __future__ import annotations

from app.core.constants.user_roles import UserRole


def is_valid_user_role(role: str) -> bool:
    """判断角色是否有效."""
    return role in UserRole.ALL


def user_role_has_permission(role: str, permission: str) -> bool:
    """判断角色是否拥有指定权限."""
    return permission in UserRole.PERMISSIONS.get(role, ())


def is_admin_role(role: str) -> bool:
    """判断是否为管理员角色."""
    return role == UserRole.ADMIN


def can_create(role: str) -> bool:
    """判断角色是否允许创建."""
    return user_role_has_permission(role, UserRole.PERM_CREATE)


def can_update(role: str) -> bool:
    """判断角色是否允许更新."""
    return user_role_has_permission(role, UserRole.PERM_UPDATE)


def can_delete(role: str) -> bool:
    """判断角色是否允许删除."""
    return user_role_has_permission(role, UserRole.PERM_DELETE)


def can_admin(role: str) -> bool:
    """判断角色是否允许管理操作."""
    return user_role_has_permission(role, UserRole.PERM_ADMIN)


def can_execute(role: str) -> bool:
    """判断角色是否允许执行操作."""
    return user_role_has_permission(role, UserRole.PERM_EXECUTE)


def get_user_role_display_name(role: str) -> str:
    """获取角色展示名称."""
    return UserRole.DISPLAY_NAMES.get(role, role)


def get_user_role_description(role: str) -> str:
    """获取角色描述."""
    return UserRole.DESCRIPTIONS.get(role, "")


def get_user_role_permissions(role: str) -> list[str]:
    """获取角色权限列表."""
    return list(UserRole.PERMISSIONS.get(role, ()))
