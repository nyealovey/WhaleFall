"""用户角色常量.

定义用户角色和权限,避免魔法字符串.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar


class UserRole:
    """用户角色常量.

    定义系统中的用户角色及其权限.
    """

    # 角色值
    ADMIN: ClassVar[str] = "admin"  # 管理员
    USER: ClassVar[str] = "user"  # 普通用户
    VIEWER: ClassVar[str] = "viewer"  # 查看者(只读)

    # 所有角色
    ALL: ClassVar[tuple[str, ...]] = (ADMIN, USER, VIEWER)

    # 权限定义

    # 基础权限
    PERM_READ: ClassVar[str] = "read"  # 读取权限
    PERM_CREATE: ClassVar[str] = "create"  # 创建权限
    PERM_UPDATE: ClassVar[str] = "update"  # 更新权限
    PERM_DELETE: ClassVar[str] = "delete"  # 删除权限
    PERM_ADMIN: ClassVar[str] = "admin"  # 管理权限
    PERM_EXECUTE: ClassVar[str] = "execute"  # 执行权限

    # 角色权限映射
    PERMISSIONS: ClassVar[Mapping[str, tuple[str, ...]]] = MappingProxyType(
        {
            ADMIN: (PERM_READ, PERM_CREATE, PERM_UPDATE, PERM_DELETE, PERM_ADMIN, PERM_EXECUTE),
            USER: (PERM_READ, PERM_CREATE, PERM_UPDATE, PERM_DELETE, PERM_EXECUTE),
            VIEWER: (PERM_READ,),
        },
    )

    # 角色显示名称
    DISPLAY_NAMES: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            ADMIN: "管理员",
            USER: "用户",
            VIEWER: "查看者",
        },
    )

    # 角色描述
    DESCRIPTIONS: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            ADMIN: "拥有系统所有权限,可以管理用户和系统配置",
            USER: "可以创建、修改、删除数据,执行同步任务",
            VIEWER: "只能查看数据,不能进行任何修改操作",
        },
    )
