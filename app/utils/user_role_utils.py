"""用户角色工具.

从 `app/core/constants/user_roles.py` 读取静态映射,提供权限判断/展示文案等纯函数.
"""

from __future__ import annotations

from app.core.constants.user_roles import UserRole


def get_user_role_display_name(role: str) -> str:
    """获取角色展示名称."""
    return UserRole.DISPLAY_NAMES.get(role, role)


def get_user_role_permissions(role: str) -> list[str]:
    """获取角色权限列表."""
    return list(UserRole.PERMISSIONS.get(role, ()))
