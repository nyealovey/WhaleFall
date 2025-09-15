"""
泰摸鱼吧 - 权限配置数据模型
"""

from datetime import datetime

from app import db
from app.utils.time_utils import now


class PermissionConfig(db.Model):
    """权限配置数据模型"""

    __tablename__ = "permission_configs"

    id = db.Column(db.Integer, primary_key=True)
    db_type = db.Column(db.String(50), nullable=False)  # 数据库类型：mysql, postgresql, sqlserver, oracle
    category = db.Column(
        db.String(50), nullable=False
    )  # 权限类别：global_privileges, database_privileges, server_roles, database_roles, server_permissions
    permission_name = db.Column(db.String(255), nullable=False)  # 权限名称
    description = db.Column(db.Text, nullable=True)  # 权限描述
    is_active = db.Column(db.Boolean, default=True)  # 是否启用
    sort_order = db.Column(db.Integer, default=0)  # 排序顺序
    created_at = db.Column(db.DateTime(timezone=True), default=now)
    updated_at = db.Column(db.DateTime(timezone=True), default=now, onupdate=now)

    # 唯一约束：同一数据库类型的同一类别下，权限名称不能重复
    __table_args__ = (
        db.UniqueConstraint("db_type", "category", "permission_name", name="uq_permission_config"),
        db.Index("idx_permission_config_db_type", "db_type"),
        db.Index("idx_permission_config_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<PermissionConfig {self.db_type}.{self.category}.{self.permission_name}>"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "db_type": self.db_type,
            "category": self.category,
            "permission_name": self.permission_name,
            "description": self.description,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def get_permissions_by_db_type(cls, db_type: str) -> dict:
        """根据数据库类型获取权限配置"""
        permissions = (
            cls.query.filter_by(db_type=db_type, is_active=True)
            .order_by(cls.category, cls.sort_order, cls.permission_name)
            .all()
        )

        # 按类别分组
        result = {}
        for perm in permissions:
            if perm.category not in result:
                result[perm.category] = []
            result[perm.category].append({"name": perm.permission_name, "description": perm.description})

        return result

    @classmethod
    def init_default_permissions(cls) -> None:
        """初始化默认权限配置"""
        # 检查是否已经初始化过
        if cls.query.first():
            return

        # MySQL权限配置
        mysql_permissions = [
            # 全局权限（服务器权限）
            ("mysql", "global_privileges", "ALTER", "修改表结构", 1),
            ("mysql", "global_privileges", "ALTER ROUTINE", "修改存储过程和函数", 2),
            ("mysql", "global_privileges", "CREATE", "创建数据库和表", 3),
            ("mysql", "global_privileges", "CREATE ROUTINE", "创建存储过程和函数", 4),
            ("mysql", "global_privileges", "CREATE TEMPORARY TABLES", "创建临时表", 5),
            ("mysql", "global_privileges", "CREATE USER", "创建用户权限", 6),
            ("mysql", "global_privileges", "CREATE VIEW", "创建视图", 7),
            ("mysql", "global_privileges", "DELETE", "删除数据", 8),
            ("mysql", "global_privileges", "DROP", "删除数据库和表", 9),
            ("mysql", "global_privileges", "EVENT", "创建、修改、删除事件", 10),
            ("mysql", "global_privileges", "EXECUTE", "执行存储过程和函数", 11),
            ("mysql", "global_privileges", "FILE", "文件操作权限", 12),
            (
                "mysql",
                "global_privileges",
                "GRANT OPTION",
                "授权权限，可以授予其他用户权限",
                13,
            ),
            ("mysql", "global_privileges", "INDEX", "创建和删除索引", 14),
            ("mysql", "global_privileges", "INSERT", "插入数据", 15),
            ("mysql", "global_privileges", "LOCK TABLES", "锁定表", 16),
            ("mysql", "global_privileges", "PROCESS", "查看所有进程", 17),
            ("mysql", "global_privileges", "REFERENCES", "引用权限", 18),
            ("mysql", "global_privileges", "RELOAD", "重载权限表", 19),
            ("mysql", "global_privileges", "REPLICATION CLIENT", "复制客户端权限", 20),
            ("mysql", "global_privileges", "REPLICATION SLAVE", "复制从库权限", 21),
            ("mysql", "global_privileges", "SELECT", "查询数据", 22),
            ("mysql", "global_privileges", "SHOW DATABASES", "显示所有数据库", 23),
            ("mysql", "global_privileges", "SHOW VIEW", "显示视图", 24),
            ("mysql", "global_privileges", "SHUTDOWN", "关闭MySQL服务器", 25),
            ("mysql", "global_privileges", "SUPER", "超级权限，可以执行任何操作", 26),
            ("mysql", "global_privileges", "TRIGGER", "创建和删除触发器", 27),
            ("mysql", "global_privileges", "UPDATE", "更新数据", 28),
            ("mysql", "global_privileges", "USAGE", "无权限，仅用于连接", 29),
            # 数据库权限
            ("mysql", "database_privileges", "CREATE", "创建数据库和表", 1),
            ("mysql", "database_privileges", "DROP", "删除数据库和表", 2),
            ("mysql", "database_privileges", "ALTER", "修改数据库和表结构", 3),
            ("mysql", "database_privileges", "INDEX", "创建和删除索引", 4),
            ("mysql", "database_privileges", "INSERT", "插入数据", 5),
            ("mysql", "database_privileges", "UPDATE", "更新数据", 6),
            ("mysql", "database_privileges", "DELETE", "删除数据", 7),
            ("mysql", "database_privileges", "SELECT", "查询数据", 8),
            (
                "mysql",
                "database_privileges",
                "CREATE TEMPORARY TABLES",
                "创建临时表",
                9,
            ),
            ("mysql", "database_privileges", "LOCK TABLES", "锁定表", 10),
            ("mysql", "database_privileges", "EXECUTE", "执行存储过程和函数", 11),
            ("mysql", "database_privileges", "CREATE VIEW", "创建视图", 12),
            ("mysql", "database_privileges", "SHOW VIEW", "显示视图", 13),
            (
                "mysql",
                "database_privileges",
                "CREATE ROUTINE",
                "创建存储过程和函数",
                14,
            ),
            ("mysql", "database_privileges", "ALTER ROUTINE", "修改存储过程和函数", 15),
            ("mysql", "database_privileges", "EVENT", "创建、修改、删除事件", 16),
            ("mysql", "database_privileges", "TRIGGER", "创建和删除触发器", 17),
        ]

        # SQL Server权限配置
        sqlserver_permissions = [
            # 服务器角色
            ("sqlserver", "server_roles", "sysadmin", "系统管理员", 1),
            ("sqlserver", "server_roles", "serveradmin", "服务器管理员", 2),
            ("sqlserver", "server_roles", "securityadmin", "安全管理员", 3),
            ("sqlserver", "server_roles", "processadmin", "进程管理员", 4),
            ("sqlserver", "server_roles", "setupadmin", "设置管理员", 5),
            ("sqlserver", "server_roles", "bulkadmin", "批量操作管理员", 6),
            ("sqlserver", "server_roles", "diskadmin", "磁盘管理员", 7),
            ("sqlserver", "server_roles", "dbcreator", "数据库创建者", 8),
            ("sqlserver", "server_roles", "public", "公共角色", 9),
            # 数据库角色
            ("sqlserver", "database_roles", "db_owner", "数据库所有者", 1),
            ("sqlserver", "database_roles", "db_accessadmin", "访问管理员", 2),
            ("sqlserver", "database_roles", "db_securityadmin", "安全管理员", 3),
            ("sqlserver", "database_roles", "db_ddladmin", "DDL管理员", 4),
            ("sqlserver", "database_roles", "db_backupoperator", "备份操作员", 5),
            ("sqlserver", "database_roles", "db_datareader", "数据读取者", 6),
            ("sqlserver", "database_roles", "db_datawriter", "数据写入者", 7),
            ("sqlserver", "database_roles", "db_denydatareader", "拒绝数据读取", 8),
            ("sqlserver", "database_roles", "db_denydatawriter", "拒绝数据写入", 9),
            # 服务器权限
            ("sqlserver", "server_permissions", "CONTROL SERVER", "控制服务器", 1),
            ("sqlserver", "server_permissions", "ALTER ANY LOGIN", "修改任意登录", 2),
            (
                "sqlserver",
                "server_permissions",
                "ALTER ANY SERVER ROLE",
                "修改任意服务器角色",
                3,
            ),
            (
                "sqlserver",
                "server_permissions",
                "CREATE ANY DATABASE",
                "创建任意数据库",
                4,
            ),
            (
                "sqlserver",
                "server_permissions",
                "ALTER ANY DATABASE",
                "修改任意数据库",
                5,
            ),
            (
                "sqlserver",
                "server_permissions",
                "VIEW SERVER STATE",
                "查看服务器状态",
                6,
            ),
            (
                "sqlserver",
                "server_permissions",
                "ALTER SERVER STATE",
                "修改服务器状态",
                7,
            ),
            ("sqlserver", "server_permissions", "ALTER SETTINGS", "修改设置", 8),
            ("sqlserver", "server_permissions", "ALTER TRACE", "修改跟踪", 9),
            (
                "sqlserver",
                "server_permissions",
                "AUTHENTICATE SERVER",
                "服务器身份验证",
                10,
            ),
            ("sqlserver", "server_permissions", "BACKUP DATABASE", "备份数据库", 11),
            ("sqlserver", "server_permissions", "BACKUP LOG", "备份日志", 12),
            ("sqlserver", "server_permissions", "CHECKPOINT", "检查点", 13),
            ("sqlserver", "server_permissions", "CONNECT SQL", "连接SQL", 14),
            ("sqlserver", "server_permissions", "SHUTDOWN", "关闭服务器", 15),
            (
                "sqlserver",
                "server_permissions",
                "IMPERSONATE ANY LOGIN",
                "模拟任意登录",
                16,
            ),
            (
                "sqlserver",
                "server_permissions",
                "VIEW ANY DEFINITION",
                "查看任意定义",
                17,
            ),
            (
                "sqlserver",
                "server_permissions",
                "VIEW ANY COLUMN ENCRYPTION KEY DEFINITION",
                "查看任意列加密密钥定义",
                18,
            ),
            (
                "sqlserver",
                "server_permissions",
                "VIEW ANY COLUMN MASTER KEY DEFINITION",
                "查看任意列主密钥定义",
                19,
            ),
            # 数据库权限
            ("sqlserver", "database_privileges", "SELECT", "查询数据", 1),
            ("sqlserver", "database_privileges", "INSERT", "插入数据", 2),
            ("sqlserver", "database_privileges", "UPDATE", "更新数据", 3),
            ("sqlserver", "database_privileges", "DELETE", "删除数据", 4),
            ("sqlserver", "database_privileges", "CREATE", "创建对象", 5),
            (
                "sqlserver",
                "database_privileges",
                "ALTER",
                "修改/删除对象（包含DROP功能）",
                6,
            ),
            ("sqlserver", "database_privileges", "EXECUTE", "执行存储过程", 7),
            ("sqlserver", "database_privileges", "CONTROL", "完全控制权限", 8),
            ("sqlserver", "database_privileges", "REFERENCES", "引用权限", 9),
            ("sqlserver", "database_privileges", "VIEW DEFINITION", "查看定义", 10),
            ("sqlserver", "database_privileges", "TAKE OWNERSHIP", "获取所有权", 11),
            ("sqlserver", "database_privileges", "IMPERSONATE", "模拟权限", 12),
            ("sqlserver", "database_privileges", "CREATE SCHEMA", "创建架构", 13),
            (
                "sqlserver",
                "database_privileges",
                "ALTER ANY SCHEMA",
                "修改任意架构",
                14,
            ),
            ("sqlserver", "database_privileges", "CREATE TABLE", "创建表", 15),
            ("sqlserver", "database_privileges", "CREATE VIEW", "创建视图", 16),
            (
                "sqlserver",
                "database_privileges",
                "CREATE PROCEDURE",
                "创建存储过程",
                17,
            ),
            ("sqlserver", "database_privileges", "CREATE FUNCTION", "创建函数", 18),
            ("sqlserver", "database_privileges", "CREATE TRIGGER", "创建触发器", 19),
        ]

        # Oracle权限配置
        oracle_permissions = [
            # 系统权限
            ("oracle", "system_privileges", "CREATE SESSION", "创建会话权限", 1),
            ("oracle", "system_privileges", "CREATE USER", "创建用户权限", 2),
            ("oracle", "system_privileges", "ALTER USER", "修改用户权限", 3),
            ("oracle", "system_privileges", "DROP USER", "删除用户权限", 4),
            ("oracle", "system_privileges", "CREATE ROLE", "创建角色权限", 5),
            ("oracle", "system_privileges", "ALTER ROLE", "修改角色权限", 6),
            ("oracle", "system_privileges", "DROP ROLE", "删除角色权限", 7),
            ("oracle", "system_privileges", "GRANT ANY PRIVILEGE", "授予任意权限", 8),
            ("oracle", "system_privileges", "GRANT ANY ROLE", "授予任意角色", 9),
            ("oracle", "system_privileges", "CREATE TABLE", "创建表权限", 10),
            ("oracle", "system_privileges", "CREATE ANY TABLE", "创建任意表权限", 11),
            ("oracle", "system_privileges", "ALTER ANY TABLE", "修改任意表权限", 12),
            ("oracle", "system_privileges", "DROP ANY TABLE", "删除任意表权限", 13),
            ("oracle", "system_privileges", "SELECT ANY TABLE", "查询任意表权限", 14),
            ("oracle", "system_privileges", "INSERT ANY TABLE", "插入任意表权限", 15),
            ("oracle", "system_privileges", "UPDATE ANY TABLE", "更新任意表权限", 16),
            ("oracle", "system_privileges", "DELETE ANY TABLE", "删除任意表权限", 17),
            ("oracle", "system_privileges", "CREATE INDEX", "创建索引权限", 18),
            ("oracle", "system_privileges", "CREATE ANY INDEX", "创建任意索引权限", 19),
            ("oracle", "system_privileges", "ALTER ANY INDEX", "修改任意索引权限", 20),
            ("oracle", "system_privileges", "DROP ANY INDEX", "删除任意索引权限", 21),
            ("oracle", "system_privileges", "CREATE PROCEDURE", "创建存储过程权限", 22),
            (
                "oracle",
                "system_privileges",
                "CREATE ANY PROCEDURE",
                "创建任意存储过程权限",
                23,
            ),
            (
                "oracle",
                "system_privileges",
                "ALTER ANY PROCEDURE",
                "修改任意存储过程权限",
                24,
            ),
            (
                "oracle",
                "system_privileges",
                "DROP ANY PROCEDURE",
                "删除任意存储过程权限",
                25,
            ),
            (
                "oracle",
                "system_privileges",
                "EXECUTE ANY PROCEDURE",
                "执行任意存储过程权限",
                26,
            ),
            ("oracle", "system_privileges", "CREATE SEQUENCE", "创建序列权限", 27),
            (
                "oracle",
                "system_privileges",
                "CREATE ANY SEQUENCE",
                "创建任意序列权限",
                28,
            ),
            (
                "oracle",
                "system_privileges",
                "ALTER ANY SEQUENCE",
                "修改任意序列权限",
                29,
            ),
            (
                "oracle",
                "system_privileges",
                "DROP ANY SEQUENCE",
                "删除任意序列权限",
                30,
            ),
            (
                "oracle",
                "system_privileges",
                "SELECT ANY SEQUENCE",
                "查询任意序列权限",
                31,
            ),
            ("oracle", "system_privileges", "CREATE VIEW", "创建视图权限", 32),
            ("oracle", "system_privileges", "CREATE ANY VIEW", "创建任意视图权限", 33),
            ("oracle", "system_privileges", "DROP ANY VIEW", "删除任意视图权限", 34),
            ("oracle", "system_privileges", "CREATE TRIGGER", "创建触发器权限", 35),
            (
                "oracle",
                "system_privileges",
                "CREATE ANY TRIGGER",
                "创建任意触发器权限",
                36,
            ),
            (
                "oracle",
                "system_privileges",
                "ALTER ANY TRIGGER",
                "修改任意触发器权限",
                37,
            ),
            (
                "oracle",
                "system_privileges",
                "DROP ANY TRIGGER",
                "删除任意触发器权限",
                38,
            ),
            ("oracle", "system_privileges", "CREATE TABLESPACE", "创建表空间权限", 39),
            ("oracle", "system_privileges", "ALTER TABLESPACE", "修改表空间权限", 40),
            ("oracle", "system_privileges", "DROP TABLESPACE", "删除表空间权限", 41),
            (
                "oracle",
                "system_privileges",
                "UNLIMITED TABLESPACE",
                "无限制表空间权限",
                42,
            ),
            (
                "oracle",
                "system_privileges",
                "CREATE DATABASE LINK",
                "创建数据库链接权限",
                43,
            ),
            (
                "oracle",
                "system_privileges",
                "CREATE PUBLIC DATABASE LINK",
                "创建公共数据库链接权限",
                44,
            ),
            (
                "oracle",
                "system_privileges",
                "DROP PUBLIC DATABASE LINK",
                "删除公共数据库链接权限",
                45,
            ),
            ("oracle", "system_privileges", "CREATE SYNONYM", "创建同义词权限", 46),
            (
                "oracle",
                "system_privileges",
                "CREATE ANY SYNONYM",
                "创建任意同义词权限",
                47,
            ),
            (
                "oracle",
                "system_privileges",
                "CREATE PUBLIC SYNONYM",
                "创建公共同义词权限",
                48,
            ),
            (
                "oracle",
                "system_privileges",
                "DROP ANY SYNONYM",
                "删除任意同义词权限",
                49,
            ),
            (
                "oracle",
                "system_privileges",
                "DROP PUBLIC SYNONYM",
                "删除公共同义词权限",
                50,
            ),
            ("oracle", "system_privileges", "AUDIT SYSTEM", "系统审计权限", 51),
            ("oracle", "system_privileges", "AUDIT ANY", "任意审计权限", 52),
            (
                "oracle",
                "system_privileges",
                "EXEMPT ACCESS POLICY",
                "豁免访问策略权限",
                53,
            ),
            (
                "oracle",
                "system_privileges",
                "EXEMPT REDACTION POLICY",
                "豁免数据脱敏策略权限",
                54,
            ),
            ("oracle", "system_privileges", "SYSDBA", "系统数据库管理员权限", 55),
            ("oracle", "system_privileges", "SYSOPER", "系统操作员权限", 56),
            # Oracle预定义角色
            ("oracle", "roles", "CONNECT", "连接角色，基本连接权限", 1),
            ("oracle", "roles", "RESOURCE", "资源角色，创建对象权限", 2),
            ("oracle", "roles", "DBA", "数据库管理员角色，所有系统权限", 3),
            ("oracle", "roles", "EXP_FULL_DATABASE", "导出完整数据库角色", 4),
            ("oracle", "roles", "IMP_FULL_DATABASE", "导入完整数据库角色", 5),
            ("oracle", "roles", "RECOVERY_CATALOG_OWNER", "恢复目录所有者角色", 6),
            ("oracle", "roles", "AUDIT_ADMIN", "审计管理员角色", 7),
            ("oracle", "roles", "AUDIT_VIEWER", "审计查看者角色", 8),
            ("oracle", "roles", "AUTHENTICATEDUSER", "认证用户角色", 9),
            ("oracle", "roles", "AQ_ADMINISTRATOR_ROLE", "高级队列管理员角色", 10),
            ("oracle", "roles", "AQ_USER_ROLE", "高级队列用户角色", 11),
            ("oracle", "roles", "CONNECT_ROLE", "连接角色（新版本）", 12),
            ("oracle", "roles", "RESOURCE_ROLE", "资源角色（新版本）", 13),
            ("oracle", "roles", "SCHEDULER_ADMIN", "调度器管理员角色", 14),
            ("oracle", "roles", "HS_ADMIN_ROLE", "异构服务管理员角色", 15),
            ("oracle", "roles", "GATHER_SYSTEM_STATISTICS", "收集系统统计信息角色", 16),
            (
                "oracle",
                "roles",
                "LOGSTDBY_ADMINISTRATOR",
                "逻辑备用数据库管理员角色",
                17,
            ),
            ("oracle", "roles", "DBFS_ROLE", "数据库文件系统角色", 18),
            ("oracle", "roles", "XDBADMIN", "XML数据库管理员角色", 19),
            ("oracle", "roles", "XDBWEBSERVICES", "XML数据库Web服务角色", 20),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_OVER_HTTP",
                "HTTP上的XML数据库Web服务角色",
                21,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_PUBLIC",
                "公共XML数据库Web服务角色",
                22,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL",
                "凭据XML数据库Web服务角色",
                23,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL_AND_ACL",
                "凭据和ACL的XML数据库Web服务角色",
                24,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_ACL",
                "ACL的XML数据库Web服务角色",
                25,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL_AND_ACL_AND_PUBLIC",
                "凭据、ACL和公共的XML数据库Web服务角色",
                26,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL_AND_ACL_AND_PUBLIC_AND_HTTP",
                "凭据、ACL、公共和HTTP的XML数据库Web服务角色",
                27,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL_AND_ACL_AND_PUBLIC_AND_HTTP_AND_HTTPS",
                "凭据、ACL、公共、HTTP和HTTPS的XML数据库Web服务角色",
                28,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL_AND_ACL_AND_PUBLIC_AND_HTTP_AND_HTTPS_AND_FTP",
                "凭据、ACL、公共、HTTP、HTTPS和FTP的XML数据库Web服务角色",
                29,
            ),
            (
                "oracle",
                "roles",
                "XDB_WEBSERVICES_WITH_CREDENTIAL_AND_ACL_AND_PUBLIC_AND_HTTP_AND_HTTPS_AND_FTP_AND_FTPS",
                "凭据、ACL、公共、HTTP、HTTPS、FTP和FTPS的XML数据库Web服务角色",
                30,
            ),
            # 表空间权限
            (
                "oracle",
                "tablespace_privileges",
                "CREATE TABLESPACE",
                "创建表空间权限",
                1,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "ALTER TABLESPACE",
                "修改表空间权限",
                2,
            ),
            ("oracle", "tablespace_privileges", "DROP TABLESPACE", "删除表空间权限", 3),
            (
                "oracle",
                "tablespace_privileges",
                "MANAGE TABLESPACE",
                "管理表空间权限",
                4,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "UNLIMITED TABLESPACE",
                "无限制表空间权限",
                5,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "CREATE ANY TABLESPACE",
                "创建任意表空间权限",
                6,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "ALTER ANY TABLESPACE",
                "修改任意表空间权限",
                7,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "DROP ANY TABLESPACE",
                "删除任意表空间权限",
                8,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "MANAGE ANY TABLESPACE",
                "管理任意表空间权限",
                9,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "SELECT ANY TABLESPACE",
                "查询任意表空间权限",
                10,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "INSERT ANY TABLESPACE",
                "插入任意表空间权限",
                11,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "UPDATE ANY TABLESPACE",
                "更新任意表空间权限",
                12,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "DELETE ANY TABLESPACE",
                "删除任意表空间权限",
                13,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "EXECUTE ANY TABLESPACE",
                "执行任意表空间权限",
                14,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "DEBUG ANY TABLESPACE",
                "调试任意表空间权限",
                15,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "FLASHBACK ANY TABLESPACE",
                "闪回任意表空间权限",
                16,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "ON COMMIT REFRESH ANY TABLESPACE",
                "提交时刷新任意表空间权限",
                17,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "QUERY REWRITE ANY TABLESPACE",
                "查询重写任意表空间权限",
                18,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "UNDER ANY TABLESPACE",
                "继承任意表空间权限",
                19,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "WRITE ANY TABLESPACE",
                "写入任意表空间权限",
                20,
            ),
            (
                "oracle",
                "tablespace_privileges",
                "READ ANY TABLESPACE",
                "读取任意表空间权限",
                21,
            ),
            # 表空间配额
            ("oracle", "tablespace_quotas", "UNLIMITED", "无限制表空间配额", 1),
            ("oracle", "tablespace_quotas", "DEFAULT", "默认表空间配额", 2),
            ("oracle", "tablespace_quotas", "QUOTA", "指定大小表空间配额", 3),
            ("oracle", "tablespace_quotas", "NO QUOTA", "无表空间配额", 4),
            ("oracle", "tablespace_quotas", "QUOTA 1M", "1MB表空间配额", 5),
            ("oracle", "tablespace_quotas", "QUOTA 10M", "10MB表空间配额", 6),
            ("oracle", "tablespace_quotas", "QUOTA 100M", "100MB表空间配额", 7),
            ("oracle", "tablespace_quotas", "QUOTA 1G", "1GB表空间配额", 8),
            ("oracle", "tablespace_quotas", "QUOTA 10G", "10GB表空间配额", 9),
            ("oracle", "tablespace_quotas", "QUOTA 100G", "100GB表空间配额", 10),
            ("oracle", "tablespace_quotas", "QUOTA 1T", "1TB表空间配额", 11),
            ("oracle", "tablespace_quotas", "QUOTA 10T", "10TB表空间配额", 12),
            ("oracle", "tablespace_quotas", "QUOTA 100T", "100TB表空间配额", 13),
            ("oracle", "tablespace_quotas", "QUOTA 1P", "1PB表空间配额", 14),
            ("oracle", "tablespace_quotas", "QUOTA 10P", "10PB表空间配额", 15),
            ("oracle", "tablespace_quotas", "QUOTA 100P", "100PB表空间配额", 16),
            ("oracle", "tablespace_quotas", "QUOTA 1E", "1EB表空间配额", 17),
            ("oracle", "tablespace_quotas", "QUOTA 10E", "10EB表空间配额", 18),
            ("oracle", "tablespace_quotas", "QUOTA 100E", "100EB表空间配额", 19),
            ("oracle", "tablespace_quotas", "QUOTA 1Z", "1ZB表空间配额", 20),
            ("oracle", "tablespace_quotas", "QUOTA 10Z", "10ZB表空间配额", 21),
            ("oracle", "tablespace_quotas", "QUOTA 100Z", "100ZB表空间配额", 22),
            ("oracle", "tablespace_quotas", "QUOTA 1Y", "1YB表空间配额", 23),
            ("oracle", "tablespace_quotas", "QUOTA 10Y", "10YB表空间配额", 24),
            ("oracle", "tablespace_quotas", "QUOTA 100Y", "100YB表空间配额", 25),
        ]

        # 批量插入权限配置
        all_permissions = mysql_permissions + sqlserver_permissions + oracle_permissions

        for (
            db_type,
            category,
            permission_name,
            description,
            sort_order,
        ) in all_permissions:
            perm = cls(
                db_type=db_type,
                category=category,
                permission_name=permission_name,
                description=description,
                sort_order=sort_order,
            )
            db.session.add(perm)

        try:
            db.session.commit()
            from app.utils.structlog_config import get_system_logger

            system_logger = get_system_logger()
            system_logger.info(
                "成功初始化权限配置",
                module="permission_config",
                count=len(all_permissions),
            )
        except Exception as e:
            db.session.rollback()
            from app.utils.structlog_config import get_system_logger

            system_logger = get_system_logger()
            system_logger.error("初始化权限配置失败", module="permission_config", exception=e)
            raise
