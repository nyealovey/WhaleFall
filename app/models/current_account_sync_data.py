"""
泰摸鱼吧 - 账户当前状态同步数据模型
"""

from datetime import datetime

from app import db
from app.models.base_sync_data import BaseSyncData
from app.utils.timezone import now


class CurrentAccountSyncData(BaseSyncData):
    """账户当前状态表（支持复杂权限结构）"""

    __tablename__ = "current_account_sync_data"

    __table_args__ = (
        db.UniqueConstraint("instance_id", "db_type", "username", name="uq_current_account_sync"),
        db.Index("idx_instance_dbtype", "instance_id", "db_type"),
        db.Index("idx_deleted", "is_deleted"),
        db.Index("idx_username", "username"),
    )

    username = db.Column(db.String(255), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)

    # MySQL权限字段
    global_privileges = db.Column(db.JSON, nullable=True)  # MySQL全局权限
    database_privileges = db.Column(db.JSON, nullable=True)  # MySQL数据库权限

    # PostgreSQL权限字段
    predefined_roles = db.Column(db.JSON, nullable=True)  # PostgreSQL预定义角色
    role_attributes = db.Column(db.JSON, nullable=True)  # PostgreSQL角色属性
    database_privileges_pg = db.Column(db.JSON, nullable=True)  # PostgreSQL数据库权限
    tablespace_privileges = db.Column(db.JSON, nullable=True)  # PostgreSQL表空间权限

    # SQL Server权限字段
    server_roles = db.Column(db.JSON, nullable=True)  # SQL Server服务器角色
    server_permissions = db.Column(db.JSON, nullable=True)  # SQL Server服务器权限
    database_roles = db.Column(db.JSON, nullable=True)  # SQL Server数据库角色
    database_permissions = db.Column(db.JSON, nullable=True)  # SQL Server数据库权限

    # Oracle权限字段（移除表空间配额）
    oracle_roles = db.Column(db.JSON, nullable=True)  # Oracle角色
    system_privileges = db.Column(db.JSON, nullable=True)  # Oracle系统权限
    tablespace_privileges_oracle = db.Column(db.JSON, nullable=True)  # Oracle表空间权限

    # 通用扩展字段
    type_specific = db.Column(db.JSON, nullable=True)  # 其他类型特定字段

    # 时间戳和状态字段
    last_sync_time = db.Column(db.DateTime(timezone=True), default=now, index=True)
    last_change_type = db.Column(db.String(20), default="add")  # 'add', 'modify_privilege', 'modify_other', 'delete'
    last_change_time = db.Column(db.DateTime(timezone=True), default=now, index=True)

    # 删除标记（不支持恢复）
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_time = db.Column(db.DateTime(timezone=True), nullable=True, index=True)

    # 关联实例
    instance = db.relationship("Instance", backref="current_account_sync_data")

    def __repr__(self) -> str:
        return f"<CurrentAccountSyncData {self.username}@{self.db_type}>"

    @property
    def is_active(self) -> bool:
        """判断账户是否激活（根据数据库类型）"""
        if self.is_deleted:
            return False
            
        if self.db_type == "postgresql":
            # PostgreSQL: 检查can_login属性
            role_attributes = self.role_attributes or {}
            can_login = role_attributes.get("can_login")
            return can_login is True
            
        elif self.db_type == "mysql":
            # MySQL: 检查is_locked属性
            type_specific = self.type_specific or {}
            is_locked = type_specific.get("is_locked")
            return is_locked is not True
            
        elif self.db_type == "sqlserver":
            # SQL Server: 检查is_disabled属性
            type_specific = self.type_specific or {}
            is_disabled = type_specific.get("is_disabled")
            return is_disabled is not True
            
        elif self.db_type == "oracle":
            # Oracle: 检查account_status
            type_specific = self.type_specific or {}
            account_status = type_specific.get("account_status", "")
            return account_status.upper() == "OPEN"
            
        # 默认返回True（未知数据库类型）
        return True

    @property
    def is_locked(self) -> bool:
        """判断账户是否被锁定（根据数据库类型）"""
        if self.is_deleted:
            return True
            
        if self.db_type == "postgresql":
            # PostgreSQL: 检查can_login属性
            role_attributes = self.role_attributes or {}
            can_login = role_attributes.get("can_login")
            return can_login is False
            
        elif self.db_type == "mysql":
            # MySQL: 检查is_locked属性
            type_specific = self.type_specific or {}
            is_locked = type_specific.get("is_locked")
            return is_locked is True
            
        elif self.db_type == "sqlserver":
            # SQL Server: 检查is_disabled属性
            type_specific = self.type_specific or {}
            is_disabled = type_specific.get("is_disabled")
            return is_disabled is True
            
        elif self.db_type == "oracle":
            # Oracle: 检查account_status
            type_specific = self.type_specific or {}
            account_status = type_specific.get("account_status", "")
            return account_status.upper() in ["LOCKED", "EXPIRED", "EXPIRED(GRACE)"]
            
        # 默认返回False（未知数据库类型）
        return False

    def to_dict(self) -> dict:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "username": self.username,
                "is_superuser": self.is_superuser,
                "global_privileges": self.global_privileges,
                "database_privileges": self.database_privileges,
                "predefined_roles": self.predefined_roles,
                "role_attributes": self.role_attributes,
                "database_privileges_pg": self.database_privileges_pg,
                "tablespace_privileges": self.tablespace_privileges,
                "server_roles": self.server_roles,
                "server_permissions": self.server_permissions,
                "database_roles": self.database_roles,
                "database_permissions": self.database_permissions,
                "oracle_roles": self.oracle_roles,
                "system_privileges": self.system_privileges,
                "tablespace_privileges_oracle": self.tablespace_privileges_oracle,
                "type_specific": self.type_specific,
                "last_sync_time": (self.last_sync_time.isoformat() if self.last_sync_time else None),
                "last_change_type": self.last_change_type,
                "last_change_time": (self.last_change_time.isoformat() if self.last_change_time else None),
                "is_deleted": self.is_deleted,
                "deleted_time": (self.deleted_time.isoformat() if self.deleted_time else None),
            }
        )
        return base_dict

    def get_permissions_by_db_type(self) -> dict:
        """根据数据库类型获取权限信息"""
        if self.db_type == "mysql":
            return {
                "global_privileges": self.global_privileges,
                "database_privileges": self.database_privileges,
                "type_specific": self.type_specific,
            }
        if self.db_type == "postgresql":
            return {
                "predefined_roles": self.predefined_roles,
                "role_attributes": self.role_attributes,
                "database_privileges": self.database_privileges_pg,
                "tablespace_privileges": self.tablespace_privileges,
                "type_specific": self.type_specific,
            }
        if self.db_type == "sqlserver":
            return {
                "server_roles": self.server_roles,
                "server_permissions": self.server_permissions,
                "database_roles": self.database_roles,
                "database_permissions": self.database_permissions,
                "type_specific": self.type_specific,
            }
        if self.db_type == "oracle":
            return {
                "oracle_roles": self.oracle_roles,
                "system_privileges": self.system_privileges,
                "tablespace_privileges": self.tablespace_privileges_oracle,
                "type_specific": self.type_specific,
            }
        return {}

    def get_can_grant_status(self) -> bool:
        """获取账户是否有授权权限"""
        try:
            if self.db_type == "mysql":
                # MySQL中检查是否有GRANT权限
                global_privileges = self.global_privileges or []
                for perm in global_privileges:
                    if isinstance(perm, dict) and perm.get("privilege") == "GRANT" and perm.get("granted", False):
                        return True
                return False
            if self.db_type == "postgresql":
                # PostgreSQL中检查是否有CREATEROLE属性
                role_attributes = self.role_attributes or []
                return "CREATEROLE" in role_attributes
            if self.db_type == "sqlserver":
                # SQL Server中检查是否有sysadmin角色
                server_roles = self.server_roles or []
                return "sysadmin" in server_roles
            if self.db_type == "oracle":
                # Oracle中检查是否有GRANT ANY PRIVILEGE权限
                system_privileges = self.system_privileges or []
                return "GRANT ANY PRIVILEGE" in system_privileges
            return False
        except (TypeError, AttributeError):
            return False
