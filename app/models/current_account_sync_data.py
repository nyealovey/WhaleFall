"""
鲸落 - 账户当前状态同步数据模型
"""

from app import db
from app.models.base_sync_data import BaseSyncData
from app.constants import DatabaseType
from app.utils.time_utils import time_utils


class CurrentAccountSyncData(BaseSyncData):
    """账户当前状态表（支持复杂权限结构）"""

    __tablename__ = "current_account_sync_data"

    __table_args__ = (
        db.UniqueConstraint("instance_id", "db_type", "username", name="uq_current_account_sync"),
        db.Index("idx_instance_dbtype", "instance_id", "db_type"),
        db.Index("idx_username", "username"),
    )

    instance_account_id = db.Column(db.Integer, db.ForeignKey("instance_accounts.id"), nullable=False, index=True)
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
    last_sync_time = db.Column(db.DateTime(timezone=True), default=time_utils.now, index=True)
    last_change_type = db.Column(db.String(20), default="add")  # 'add', 'modify_privilege', 'modify_other', 'delete'
    last_change_time = db.Column(db.DateTime(timezone=True), default=time_utils.now, index=True)

    # 删除标记（不支持恢复）
    # 关联实例与账户
    instance = db.relationship("Instance", backref="current_account_sync_data")
    instance_account = db.relationship("InstanceAccount", backref=db.backref("current_sync", uselist=False))

    def __repr__(self) -> str:
        return f"<CurrentAccountSyncData {self.username}@{self.db_type}>"

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
                "instance_account_id": self.instance_account_id,
            }
        )
        return base_dict

    def get_permissions_by_db_type(self) -> dict:
        """根据数据库类型获取权限信息"""
        if self.db_type == DatabaseType.MYSQL:
            return {
                "global_privileges": self.global_privileges,
                "database_privileges": self.database_privileges,
                "type_specific": self.type_specific,
            }
        if self.db_type == DatabaseType.POSTGRESQL:
            return {
                "predefined_roles": self.predefined_roles,
                "role_attributes": self.role_attributes,
                "database_privileges": self.database_privileges_pg,
                "tablespace_privileges": self.tablespace_privileges,
                "type_specific": self.type_specific,
            }
        if self.db_type == DatabaseType.SQLSERVER:
            return {
                "server_roles": self.server_roles,
                "server_permissions": self.server_permissions,
                "database_roles": self.database_roles,
                "database_permissions": self.database_permissions,
                "type_specific": self.type_specific,
            }
        if self.db_type == DatabaseType.ORACLE:
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
            if self.db_type == DatabaseType.MYSQL:
                # MySQL中检查是否有GRANT权限
                global_privileges = self.global_privileges or []
                for perm in global_privileges:
                    if isinstance(perm, dict) and perm.get("privilege") == "GRANT" and perm.get("granted", False):
                        return True
                return False
            if self.db_type == DatabaseType.POSTGRESQL:
                # PostgreSQL中检查是否有CREATEROLE属性
                role_attributes = self.role_attributes or []
                return "CREATEROLE" in role_attributes
            if self.db_type == DatabaseType.SQLSERVER:
                # SQL Server中检查是否有sysadmin角色
                server_roles = self.server_roles or []
                return "sysadmin" in server_roles
            if self.db_type == DatabaseType.ORACLE:
                # Oracle中检查是否有GRANT ANY PRIVILEGE权限
                system_privileges = self.system_privileges or []
                return "GRANT ANY PRIVILEGE" in system_privileges
            return False
        except (TypeError, AttributeError):
            return False

    @property
    def is_locked_display(self) -> bool:
        """计算显示用的账户锁定状态"""
        if not self.type_specific:
            return False

        try:
            if self.db_type == DatabaseType.MYSQL:
                # MySQL: 检查 account_locked 字段
                return self.type_specific.get("is_locked", False)

            if self.db_type == DatabaseType.POSTGRESQL:
                # PostgreSQL: 检查 can_login 属性（反向）
                return not self.type_specific.get("can_login", True)

            if self.db_type == DatabaseType.SQLSERVER:
                # SQL Server: 检查 is_disabled 字段
                return self.type_specific.get("is_disabled", False)

            if self.db_type == DatabaseType.ORACLE:
                # Oracle: 检查 account_status 字段
                account_status = self.type_specific.get("account_status", "OPEN")
                return account_status.upper() != "OPEN"

            return False
        except (TypeError, AttributeError, KeyError):
            return False
