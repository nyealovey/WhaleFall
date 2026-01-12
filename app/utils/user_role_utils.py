"""用户角色工具.

从 `app/constants/user_roles.py` 读取静态映射,提供权限判断/展示文案等纯函数.
"""

from __future__ import annotations

from app.constants.user_roles import UserRole


def is_valid_user_role(role: str) -> bool:
    return role in UserRole.ALL


def user_role_has_permission(role: str, permission: str) -> bool:
    return permission in UserRole.PERMISSIONS.get(role, ())


def is_admin_role(role: str) -> bool:
    return role == UserRole.ADMIN


def can_create(role: str) -> bool:
    return user_role_has_permission(role, UserRole.PERM_CREATE)


def can_update(role: str) -> bool:
    return user_role_has_permission(role, UserRole.PERM_UPDATE)


def can_delete(role: str) -> bool:
    return user_role_has_permission(role, UserRole.PERM_DELETE)


def can_admin(role: str) -> bool:
    return user_role_has_permission(role, UserRole.PERM_ADMIN)


def can_execute(role: str) -> bool:
    return user_role_has_permission(role, UserRole.PERM_EXECUTE)


def get_user_role_display_name(role: str) -> str:
    return UserRole.DISPLAY_NAMES.get(role, role)


def get_user_role_description(role: str) -> str:
    return UserRole.DESCRIPTIONS.get(role, "")


def get_user_role_permissions(role: str) -> list[str]:
    return list(UserRole.PERMISSIONS.get(role, ()))

