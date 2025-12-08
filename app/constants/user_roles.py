"""
用户角色常量

定义用户角色和权限，避免魔法字符串。
"""


class UserRole:
    """用户角色常量
    
    定义系统中的用户角色及其权限。
    """

    # ============================================================================
    # 角色值
    # ============================================================================
    ADMIN = "admin"             # 管理员
    USER = "user"               # 普通用户
    VIEWER = "viewer"           # 查看者（只读）

    # 所有角色
    ALL = [ADMIN, USER, VIEWER]

    # ============================================================================
    # 权限定义
    # ============================================================================

    # 基础权限
    PERM_READ = "read"          # 读取权限
    PERM_CREATE = "create"      # 创建权限
    PERM_UPDATE = "update"      # 更新权限
    PERM_DELETE = "delete"      # 删除权限
    PERM_ADMIN = "admin"        # 管理权限
    PERM_EXECUTE = "execute"    # 执行权限

    # 角色权限映射
    PERMISSIONS = {
        ADMIN: [PERM_READ, PERM_CREATE, PERM_UPDATE, PERM_DELETE, PERM_ADMIN, PERM_EXECUTE],
        USER: [PERM_READ, PERM_CREATE, PERM_UPDATE, PERM_DELETE, PERM_EXECUTE],
        VIEWER: [PERM_READ],
    }

    # 角色显示名称
    DISPLAY_NAMES = {
        ADMIN: "管理员",
        USER: "用户",
        VIEWER: "查看者",
    }

    # 角色描述
    DESCRIPTIONS = {
        ADMIN: "拥有系统所有权限，可以管理用户和系统配置",
        USER: "可以创建、修改、删除数据，执行同步任务",
        VIEWER: "只能查看数据，不能进行任何修改操作",
    }

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @classmethod
    def is_valid(cls, role: str) -> bool:
        """验证角色是否有效
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否为有效角色

        """
        return role in cls.ALL

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """检查角色是否有指定权限
        
        Args:
            role: 角色字符串
            permission: 权限字符串
            
        Returns:
            bool: 是否有权限

        """
        return permission in cls.PERMISSIONS.get(role, [])

    @classmethod
    def is_admin(cls, role: str) -> bool:
        """判断是否为管理员角色
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否为管理员

        """
        return role == cls.ADMIN

    @classmethod
    def can_create(cls, role: str) -> bool:
        """判断角色是否有创建权限
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否有创建权限

        """
        return cls.has_permission(role, cls.PERM_CREATE)

    @classmethod
    def can_update(cls, role: str) -> bool:
        """判断角色是否有更新权限
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否有更新权限

        """
        return cls.has_permission(role, cls.PERM_UPDATE)

    @classmethod
    def can_delete(cls, role: str) -> bool:
        """判断角色是否有删除权限
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否有删除权限

        """
        return cls.has_permission(role, cls.PERM_DELETE)

    @classmethod
    def can_admin(cls, role: str) -> bool:
        """判断角色是否有管理权限
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否有管理权限

        """
        return cls.has_permission(role, cls.PERM_ADMIN)

    @classmethod
    def can_execute(cls, role: str) -> bool:
        """判断角色是否有执行权限
        
        Args:
            role: 角色字符串
            
        Returns:
            bool: 是否有执行权限

        """
        return cls.has_permission(role, cls.PERM_EXECUTE)

    @classmethod
    def get_display_name(cls, role: str) -> str:
        """获取角色的显示名称
        
        Args:
            role: 角色字符串
            
        Returns:
            str: 显示名称

        """
        return cls.DISPLAY_NAMES.get(role, role)

    @classmethod
    def get_description(cls, role: str) -> str:
        """获取角色描述
        
        Args:
            role: 角色字符串
            
        Returns:
            str: 角色描述

        """
        return cls.DESCRIPTIONS.get(role, "")

    @classmethod
    def get_permissions(cls, role: str) -> list[str]:
        """获取角色的所有权限
        
        Args:
            role: 角色字符串
            
        Returns:
            list[str]: 权限列表

        """
        return cls.PERMISSIONS.get(role, [])
