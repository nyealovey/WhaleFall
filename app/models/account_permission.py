"""鲸落 - 账户权限快照数据模型."""

from app import db
from app.constants import DatabaseType
from app.models.base_sync_data import BaseSyncData
from app.utils.time_utils import time_utils


class AccountPermission(BaseSyncData):
    """账户权限快照（支持复杂权限结构）。.

    存储不同数据库类型账户的权限信息快照，支持 MySQL、PostgreSQL、
    SQL Server 和 Oracle 的权限结构。继承自 BaseSyncData。

    Attributes:
        instance_account_id: 关联的实例账户 ID。
        username: 账户名。
        is_superuser: 是否为超级用户。
        is_locked: 是否被锁定。
        global_privileges: MySQL 全局权限（JSON）。
        database_privileges: MySQL 数据库权限（JSON）。
        predefined_roles: PostgreSQL 预定义角色（JSON）。
        role_attributes: PostgreSQL 角色属性（JSON）。
        database_privileges_pg: PostgreSQL 数据库权限（JSON）。
        tablespace_privileges: PostgreSQL 表空间权限（JSON）。
        server_roles: SQL Server 服务器角色（JSON）。
        server_permissions: SQL Server 服务器权限（JSON）。
        database_roles: SQL Server 数据库角色（JSON）。
        database_permissions: SQL Server 数据库权限（JSON）。
        oracle_roles: Oracle 角色（JSON）。
        system_privileges: Oracle 系统权限（JSON）。
        tablespace_privileges_oracle: Oracle 表空间权限（JSON）。
        type_specific: 其他类型特定字段（JSON）。
        last_sync_time: 最后同步时间。

    """

    __tablename__ = "account_permission"

    __table_args__ = (
        db.UniqueConstraint("instance_id", "db_type", "username", name="uq_account_permission"),
        db.Index("idx_account_permission_instance_dbtype", "instance_id", "db_type"),
        db.Index("idx_account_permission_username", "username"),
    )

    instance_account_id = db.Column(db.Integer, db.ForeignKey("instance_accounts.id"), nullable=False, index=True)
    username = db.Column(db.String(255), nullable=False)
    is_superuser = db.Column(db.Boolean, default=False)
    is_locked = db.Column(db.Boolean, default=False, nullable=False, index=True)

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
    last_change_type = db.Column(db.String(20), default="add")
    last_change_time = db.Column(db.DateTime(timezone=True), default=time_utils.now, index=True)

    # 删除标记（不支持恢复）
    # 关联实例与账户
    instance = db.relationship("Instance", backref="account_permissions")
    instance_account = db.relationship(
        "InstanceAccount",
        backref=db.backref("current_sync", uselist=False),
    )

    def __repr__(self) -> str:
        """Return concise account permission label.

        Returns:
            str: `<AccountPermission username@db>` 格式。

        """
        return f"<AccountPermission {self.username}@{self.db_type}>"

    def to_dict(self) -> dict:
        """转换为字典。.

        Returns:
            dict: 包含权限快照及基础字段的字典。

        """
        base_dict = super().to_dict()
        base_dict.update(
            {
                "username": self.username,
                "is_superuser": self.is_superuser,
                "is_locked": self.is_locked,
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
            },
        )
        return base_dict

    def get_permissions_by_db_type(self) -> dict:
        """根据数据库类型获取权限信息。.

        Returns:
            dict: 仅包含当前数据库类型对应的权限字段。

        """
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
