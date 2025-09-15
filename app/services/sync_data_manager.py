"""
泰摸鱼吧 - 统一同步数据管理器
"""

from datetime import datetime

from app.utils.time_utils import time_utils

from app import db
from app.models.account_change_log import AccountChangeLog
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.utils.structlog_config import get_sync_logger


class SyncDataManager:
    """统一同步数据管理器"""

    def __init__(self):
        self.sync_logger = get_sync_logger()

    def sync_mysql_accounts(self, instance, conn, session_id: str) -> dict:
        """同步MySQL账户"""
        try:
            # 获取MySQL账户信息
            accounts = self._get_mysql_accounts(conn)

            synced_count = 0
            added_count = 0
            modified_count = 0

            for account_data in accounts:
                try:
                    # 使用upsert_account方法
                    account = self.upsert_account(
                        instance_id=instance.id,
                        db_type="mysql",
                        username=account_data["username"],
                        permissions_data=account_data["permissions"],
                        is_superuser=account_data.get("is_superuser", False),
                        session_id=session_id,
                    )
                    synced_count += 1
                    if account.last_change_type == "add":
                        added_count += 1
                    elif account.last_change_type == "modify_privilege":
                        modified_count += 1
                except Exception as e:
                    self.sync_logger.error(f"同步MySQL账户失败: {account_data['username']}", error=str(e))

            return {
                "success": True,
                "synced_count": synced_count,
                "added_count": added_count,
                "modified_count": modified_count,
                "removed_count": 0,
            }
        except Exception as e:
            self.sync_logger.error("MySQL账户同步失败", error=str(e))
            return {"success": False, "error": str(e)}

    def sync_postgresql_accounts(self, instance, conn, session_id: str) -> dict:
        """同步PostgreSQL账户"""
        try:
            # 获取PostgreSQL账户信息
            accounts = self._get_postgresql_accounts(conn)

            synced_count = 0
            added_count = 0
            modified_count = 0

            for account_data in accounts:
                try:
                    account = self.upsert_account(
                        instance_id=instance.id,
                        db_type="postgresql",
                        username=account_data["username"],
                        permissions_data=account_data["permissions"],
                        is_superuser=account_data.get("is_superuser", False),
                        session_id=session_id,
                    )
                    synced_count += 1
                    if account.last_change_type == "add":
                        added_count += 1
                    elif account.last_change_type == "modify_privilege":
                        modified_count += 1
                except Exception as e:
                    self.sync_logger.error(
                        f"同步PostgreSQL账户失败: {account_data['username']}",
                        error=str(e),
                    )

            return {
                "success": True,
                "synced_count": synced_count,
                "added_count": added_count,
                "modified_count": modified_count,
                "removed_count": 0,
            }
        except Exception as e:
            self.sync_logger.error("PostgreSQL账户同步失败", error=str(e))
            return {"success": False, "error": str(e)}

    def sync_sqlserver_accounts(self, instance, conn, session_id: str) -> dict:
        """同步SQL Server账户"""
        try:
            # 获取SQL Server账户信息
            accounts = self._get_sqlserver_accounts(conn)

            synced_count = 0
            added_count = 0
            modified_count = 0

            for account_data in accounts:
                try:
                    account = self.upsert_account(
                        instance_id=instance.id,
                        db_type="sqlserver",
                        username=account_data["username"],
                        permissions_data=account_data["permissions"],
                        is_superuser=account_data.get("is_superuser", False),
                        session_id=session_id,
                    )
                    synced_count += 1
                    if account.last_change_type == "add":
                        added_count += 1
                    elif account.last_change_type == "modify_privilege":
                        modified_count += 1
                except Exception as e:
                    self.sync_logger.error(
                        f"同步SQL Server账户失败: {account_data['username']}",
                        error=str(e),
                    )

            return {
                "success": True,
                "synced_count": synced_count,
                "added_count": added_count,
                "modified_count": modified_count,
                "removed_count": 0,
            }
        except Exception as e:
            self.sync_logger.error("SQL Server账户同步失败", error=str(e))
            return {"success": False, "error": str(e)}

    def sync_oracle_accounts(self, instance, conn, session_id: str) -> dict:
        """同步Oracle账户"""
        try:
            # 获取Oracle账户信息
            accounts = self._get_oracle_accounts(conn)

            synced_count = 0
            added_count = 0
            modified_count = 0

            for account_data in accounts:
                try:
                    account = self.upsert_account(
                        instance_id=instance.id,
                        db_type="oracle",
                        username=account_data["username"],
                        permissions_data=account_data["permissions"],
                        is_superuser=account_data.get("is_superuser", False),
                        session_id=session_id,
                    )
                    synced_count += 1
                    if account.last_change_type == "add":
                        added_count += 1
                    elif account.last_change_type == "modify_privilege":
                        modified_count += 1
                except Exception as e:
                    self.sync_logger.error(f"同步Oracle账户失败: {account_data['username']}", error=str(e))

            return {
                "success": True,
                "synced_count": synced_count,
                "added_count": added_count,
                "modified_count": modified_count,
                "removed_count": 0,
            }
        except Exception as e:
            self.sync_logger.error("Oracle账户同步失败", error=str(e))
            return {"success": False, "error": str(e)}

    def _get_mysql_accounts(self, conn) -> list:
        """获取MySQL账户信息"""
        try:
            # 获取过滤规则
            from app.services.database_filter_manager import DatabaseFilterManager

            filter_manager = DatabaseFilterManager()
            filter_conditions = filter_manager.get_safe_sql_filter_conditions("mysql", "User")

            # 构建查询SQL
            where_clause, params = filter_conditions
            sql = f"""
                SELECT
                    User as username,
                    Host as host,
                    Super_priv as is_superuser,
                    Grant_priv as can_grant
                FROM mysql.user
                WHERE User != '' AND {where_clause}
            """

            # 查询用户信息
            users = conn.execute_query(sql, params)

            accounts = []
            for row in users:
                username, host, is_superuser, can_grant = row

                # 获取全局权限
                grants = conn.execute_query("SHOW GRANTS FOR %s@%s", (username, host))
                grants = [row[0] for row in grants]

                # 解析权限
                global_privileges = []
                database_privileges = {}

                for grant in grants:
                    if "GRANT ALL PRIVILEGES" in grant.upper():
                        global_privileges.append("ALL PRIVILEGES")
                    elif "ON *.*" in grant:
                        # 全局权限 - 分割权限字符串
                        privs_string = grant.split("ON *.*")[0].replace("GRANT ", "").strip()
                        # 分割权限并添加到列表中
                        privs_list = [p.strip() for p in privs_string.split(",") if p.strip()]
                        for priv in privs_list:
                            if priv not in global_privileges:
                                global_privileges.append(priv)
                    elif "ON `" in grant and "`.*" in grant:
                        # 数据库权限
                        db_name = grant.split("ON `")[1].split("`.*")[0]
                        privs_string = grant.split("ON `")[0].replace("GRANT ", "").strip()
                        # 分割权限
                        privs_list = [p.strip() for p in privs_string.split(",") if p.strip()]
                        if db_name not in database_privileges:
                            database_privileges[db_name] = []
                        database_privileges[db_name].extend(privs_list)

                accounts.append(
                    {
                        "username": username,
                        "permissions": {
                            "global_privileges": global_privileges,
                            "database_privileges": database_privileges,
                            "type_specific": {
                                "host": host,
                                "can_grant": can_grant == "Y",
                            },
                        },
                        "is_superuser": is_superuser == "Y",
                    }
                )

            return accounts
        except Exception as e:
            self.sync_logger.error("获取MySQL账户失败", error=str(e))
            return []

    def _get_postgresql_accounts(self, conn) -> list:
        """获取PostgreSQL账户信息"""
        try:
            # 获取过滤规则
            from app.services.database_filter_manager import DatabaseFilterManager

            filter_manager = DatabaseFilterManager()
            filter_conditions = filter_manager.get_safe_sql_filter_conditions("postgresql", "rolname")

            # 构建查询SQL
            where_clause, params = filter_conditions
            sql = f"""
                SELECT
                    rolname as username,
                    rolsuper as is_superuser,
                    rolcreaterole as can_create_role,
                    rolcreatedb as can_create_db,
                    rolreplication as can_replicate,
                    rolbypassrls as can_bypass_rls
                FROM pg_roles
                WHERE {where_clause}
            """

            # 查询角色信息
            roles = conn.execute_query(sql, params)

            accounts = []
            for row in roles:
                username, is_superuser, can_create_role, can_create_db, can_replicate, can_bypass_rls = row

                # 获取详细的权限信息
                permissions = self._get_postgresql_permissions(conn, username, is_superuser)

                accounts.append(
                    {
                        "username": username,
                        "permissions": permissions,
                        "is_superuser": is_superuser,
                    }
                )

            return accounts
        except Exception as e:
            self.sync_logger.error("获取PostgreSQL账户失败", error=str(e))
            return []

    def _get_postgresql_permissions(self, conn, username: str, is_superuser: bool) -> dict:
        """获取PostgreSQL用户的详细权限信息"""
        try:
            permissions = {
                "predefined_roles": [],
                "role_attributes": {},
                "database_privileges": {},
                "tablespace_privileges": {},
                "system_privileges": [],
            }

            # 如果是超级用户，直接返回超级用户权限
            if is_superuser:
                permissions["role_attributes"] = {
                    "can_create_role": True,
                    "can_create_db": True,
                    "can_replicate": True,
                    "can_bypass_rls": True,
                    "can_login": True,
                    "can_inherit": True,
                }
                permissions["system_privileges"] = ["SUPERUSER"]
                return permissions

            # 获取角色属性
            role_attrs_sql = """
                SELECT
                    rolcreaterole,
                    rolcreatedb,
                    rolcanlogin,
                    rolinherit,
                    rolreplication,
                    rolbypassrls
                FROM pg_roles
                WHERE rolname = %s
            """
            role_attrs = conn.execute_query(role_attrs_sql, (username,))
            if role_attrs:
                attrs = role_attrs[0]
                permissions["role_attributes"] = {
                    "can_create_role": attrs[0],
                    "can_create_db": attrs[1],
                    "can_login": attrs[2],
                    "can_inherit": attrs[3],
                    "can_replicate": attrs[4],
                    "can_bypass_rls": attrs[5],
                }

            # 获取系统权限
            sys_privs_sql = """
                SELECT DISTINCT privilege_type
                FROM information_schema.role_usage_grants
                WHERE grantee = %s
                ORDER BY privilege_type
            """
            sys_privs = conn.execute_query(sys_privs_sql, (username,))
            permissions["system_privileges"] = [priv[0] for priv in sys_privs]

            # 获取数据库权限
            db_privs_sql = """
                SELECT
                    table_catalog,
                    privilege_type
                FROM information_schema.table_privileges
                WHERE grantee = %s
                ORDER BY table_catalog, privilege_type
            """
            db_privs = conn.execute_query(db_privs_sql, (username,))
            for priv in db_privs:
                db_name = priv[0]
                priv_type = priv[1]
                if db_name not in permissions["database_privileges"]:
                    permissions["database_privileges"][db_name] = []
                permissions["database_privileges"][db_name].append(priv_type)

            # 获取角色成员关系
            role_members_sql = """
                SELECT r.rolname
                FROM pg_auth_members m
                JOIN pg_roles r ON m.roleid = r.oid
                WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = %s)
            """
            role_members = conn.execute_query(role_members_sql, (username,))
            permissions["predefined_roles"] = [member[0] for member in role_members]

            return permissions

        except Exception as e:
            self.sync_logger.error(f"获取PostgreSQL权限失败: {username}", error=str(e))
            return {
                "predefined_roles": [],
                "role_attributes": {},
                "database_privileges": {},
                "tablespace_privileges": {},
                "system_privileges": [],
            }

    def _get_sqlserver_accounts(self, conn) -> list:
        """获取SQL Server账户信息"""
        try:
            # 获取过滤规则
            from app.services.database_filter_manager import DatabaseFilterManager

            filter_manager = DatabaseFilterManager()
            filter_conditions = filter_manager.get_safe_sql_filter_conditions("sqlserver", "name")

            # 构建查询SQL
            where_clause, params = filter_conditions
            sql = f"""
                SELECT
                    name as username,
                    is_disabled as is_disabled,
                    type_desc as login_type
                FROM sys.server_principals
                WHERE type IN ('S', 'U', 'G') AND {where_clause}
            """

            # 查询登录信息
            logins = conn.execute_query(sql, params)

            accounts = []
            for row in logins:
                username, is_disabled, login_type = row

                # 获取服务器角色
                server_roles = self._get_sqlserver_server_roles(conn, username)

                # 获取服务器权限
                server_permissions = self._get_sqlserver_server_permissions(conn, username)

                # 获取数据库角色和权限
                database_roles, database_permissions = self._get_sqlserver_database_permissions(conn, username)

                # 判断是否为超级用户（sa账户或sysadmin角色）
                is_superuser = username.lower() == "sa" or "sysadmin" in server_roles

                accounts.append(
                    {
                        "username": username,
                        "permissions": {
                            "server_roles": server_roles,
                            "server_permissions": server_permissions,
                            "database_roles": database_roles,
                            "database_permissions": database_permissions,
                        },
                        "is_superuser": is_superuser,
                    }
                )

            return accounts
        except Exception as e:
            self.sync_logger.error("获取SQL Server账户失败", error=str(e))
            return []

    def _get_sqlserver_server_roles(self, conn, username: str) -> list:
        """获取SQL Server服务器角色"""
        try:
            sql = """
                SELECT r.name
                FROM sys.server_role_members rm
                JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
                WHERE p.name = %s
            """
            roles = conn.execute_query(sql, (username,))
            return [role[0] for role in roles]
        except Exception as e:
            self.sync_logger.error(f"获取SQL Server服务器角色失败: {username}", error=str(e))
            return []

    def _get_sqlserver_server_permissions(self, conn, username: str) -> list:
        """获取SQL Server服务器权限"""
        try:
            sql = """
                SELECT permission_name
                FROM sys.server_permissions
                WHERE grantee_principal_id = (
                    SELECT principal_id
                    FROM sys.server_principals
                    WHERE name = %s
                )
                AND state = 'G'
            """
            permissions = conn.execute_query(sql, (username,))
            return [perm[0] for perm in permissions]
        except Exception as e:
            self.sync_logger.error(f"获取SQL Server服务器权限失败: {username}", error=str(e))
            return []

    def _get_sqlserver_database_permissions(self, conn, username: str) -> tuple:
        """获取SQL Server数据库角色和权限"""
        try:
            # 获取数据库角色
            database_roles = {}
            database_permissions = {}

            # 获取所有数据库列表
            databases_sql = "SELECT name FROM sys.databases WHERE state = 0"  # 只获取在线数据库
            databases = conn.execute_query(databases_sql)

            for db_row in databases:
                db_name = db_row[0]
                try:
                    # 切换到目标数据库
                    conn.execute_query(f"USE [{db_name}]")

                    # 获取数据库角色
                    roles_sql = """
                        SELECT r.name
                        FROM sys.database_role_members rm
                        JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
                        JOIN sys.database_principals p ON rm.member_principal_id = p.principal_id
                        WHERE p.name = %s
                    """
                    roles = conn.execute_query(roles_sql, (username,))
                    if roles:
                        database_roles[db_name] = [role[0] for role in roles]

                    # 获取数据库权限
                    perms_sql = """
                        SELECT permission_name
                        FROM sys.database_permissions
                        WHERE grantee_principal_id = (
                            SELECT principal_id
                            FROM sys.database_principals
                            WHERE name = %s
                        )
                        AND state = 'G'
                    """
                    permissions = conn.execute_query(perms_sql, (username,))
                    if permissions:
                        database_permissions[db_name] = [perm[0] for perm in permissions]

                except Exception as e:
                    # 如果无法访问某个数据库，跳过
                    self.sync_logger.warning(f"无法访问数据库 {db_name}: {str(e)}")
                    continue

            return database_roles, database_permissions

        except Exception as e:
            self.sync_logger.error(f"获取SQL Server数据库权限失败: {username}", error=str(e))
            return {}, {}

    def _get_oracle_accounts(self, conn) -> list:
        """获取Oracle账户信息"""
        try:
            # 获取过滤规则
            from app.services.database_filter_manager import DatabaseFilterManager

            filter_manager = DatabaseFilterManager()
            filter_conditions = filter_manager.get_safe_sql_filter_conditions("oracle", "username")

            # 构建查询SQL
            where_clause, params = filter_conditions
            sql = f"""
                SELECT
                    username,
                    account_status,
                    created,
                    expiry_date
                FROM dba_users
                WHERE {where_clause}
            """

            # 查询用户信息
            users = conn.execute_query(sql, params)

            accounts = []
            for row in users:
                username, account_status, created, expiry_date = row

                accounts.append(
                    {
                        "username": username,
                        "permissions": {
                            "oracle_roles": [],
                            "system_privileges": [],
                            "tablespace_privileges": {},
                        },
                        "is_superuser": False,
                    }
                )

            return accounts
        except Exception as e:
            self.sync_logger.error("获取Oracle账户失败", error=str(e))
            return []

    @classmethod
    def get_account_latest(
        cls,
        db_type: str,
        instance_id: int,
        username: str = None,
        include_deleted: bool = False,
    ) -> CurrentAccountSyncData | None:
        """获取账户最新状态"""
        query = CurrentAccountSyncData.query.filter_by(instance_id=instance_id, db_type=db_type)
        if username:
            query = query.filter_by(username=username)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.first()

    @classmethod
    def get_accounts_by_instance(cls, instance_id: int, include_deleted: bool = False) -> list[CurrentAccountSyncData]:
        """获取实例的所有账户"""
        query = CurrentAccountSyncData.query.filter_by(instance_id=instance_id)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()

    @classmethod
    def get_account_changes(cls, instance_id: int, db_type: str, username: str) -> list[AccountChangeLog]:
        """获取账户变更历史"""
        return (
            AccountChangeLog.query.filter_by(instance_id=instance_id, db_type=db_type, username=username)
            .order_by(AccountChangeLog.change_time.desc())
            .all()
        )

    @classmethod
    def upsert_account(
        cls,
        instance_id: int,
        db_type: str,
        username: str,
        permissions_data: dict,
        is_superuser: bool = False,
        session_id: str = None,
    ) -> CurrentAccountSyncData:
        """根据数据库类型更新账户权限"""

        if db_type == "mysql":
            return cls._upsert_mysql_account(instance_id, username, permissions_data, is_superuser, session_id)
        if db_type == "postgresql":
            return cls._upsert_postgresql_account(instance_id, username, permissions_data, is_superuser, session_id)
        if db_type == "sqlserver":
            return cls._upsert_sqlserver_account(instance_id, username, permissions_data, is_superuser, session_id)
        if db_type == "oracle":
            return cls._upsert_oracle_account(instance_id, username, permissions_data, is_superuser, session_id)
        raise ValueError(f"不支持的数据库类型: {db_type}")

    @classmethod
    def _upsert_mysql_account(
        cls,
        instance_id: int,
        username: str,
        permissions_data: dict,
        is_superuser: bool,
        session_id: str = None,
    ) -> CurrentAccountSyncData:
        """更新MySQL账户权限"""
        account = cls.get_account_latest("mysql", instance_id, username, include_deleted=True)

        if account:
            # 检查权限变更
            changes = cls._detect_mysql_changes(account, permissions_data)
            if changes:
                cls._log_changes(instance_id, "mysql", username, changes, session_id)
                cls._update_mysql_account(account, permissions_data, is_superuser)
            return account
        # 创建新账户
        account = CurrentAccountSyncData(
            instance_id=instance_id,
            db_type="mysql",
            username=username,
            global_privileges=permissions_data.get("global_privileges", []),
            database_privileges=permissions_data.get("database_privileges", {}),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            last_change_type="add",
            session_id=session_id,
        )
        db.session.add(account)
        db.session.commit()
        return account

    @classmethod
    def _upsert_postgresql_account(
        cls,
        instance_id: int,
        username: str,
        permissions_data: dict,
        is_superuser: bool,
        session_id: str = None,
    ) -> CurrentAccountSyncData:
        """更新PostgreSQL账户权限"""
        account = cls.get_account_latest("postgresql", instance_id, username, include_deleted=True)

        if account:
            # 检查权限变更
            changes = cls._detect_postgresql_changes(account, permissions_data)
            if changes:
                cls._log_changes(instance_id, "postgresql", username, changes, session_id)
                cls._update_postgresql_account(account, permissions_data, is_superuser)
            return account
        # 创建新账户
        account = CurrentAccountSyncData(
            instance_id=instance_id,
            db_type="postgresql",
            username=username,
            predefined_roles=permissions_data.get("predefined_roles", []),
            role_attributes=permissions_data.get("role_attributes", {}),
            database_privileges_pg=permissions_data.get("database_privileges", {}),
            tablespace_privileges=permissions_data.get("tablespace_privileges", {}),
            system_privileges=permissions_data.get("system_privileges", []),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            last_change_type="add",
            session_id=session_id,
        )
        db.session.add(account)
        db.session.commit()
        return account

    @classmethod
    def _upsert_sqlserver_account(
        cls,
        instance_id: int,
        username: str,
        permissions_data: dict,
        is_superuser: bool,
        session_id: str = None,
    ) -> CurrentAccountSyncData:
        """更新SQL Server账户权限"""
        account = cls.get_account_latest("sqlserver", instance_id, username, include_deleted=True)

        if account:
            # 检查权限变更
            changes = cls._detect_sqlserver_changes(account, permissions_data)
            if changes:
                cls._log_changes(instance_id, "sqlserver", username, changes, session_id)
                cls._update_sqlserver_account(account, permissions_data, is_superuser)
            return account
        # 创建新账户
        account = CurrentAccountSyncData(
            instance_id=instance_id,
            db_type="sqlserver",
            username=username,
            server_roles=permissions_data.get("server_roles", []),
            server_permissions=permissions_data.get("server_permissions", []),
            database_roles=permissions_data.get("database_roles", {}),
            database_permissions=permissions_data.get("database_permissions", {}),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            last_change_type="add",
            session_id=session_id,
        )
        db.session.add(account)
        db.session.commit()
        return account

    @classmethod
    def _upsert_oracle_account(
        cls,
        instance_id: int,
        username: str,
        permissions_data: dict,
        is_superuser: bool,
        session_id: str = None,
    ) -> CurrentAccountSyncData:
        """更新Oracle账户权限（移除表空间配额）"""
        account = cls.get_account_latest("oracle", instance_id, username, include_deleted=True)

        if account:
            # 检查权限变更
            changes = cls._detect_oracle_changes(account, permissions_data)
            if changes:
                cls._log_changes(instance_id, "oracle", username, changes, session_id)
                cls._update_oracle_account(account, permissions_data, is_superuser)
            return account
        # 创建新账户
        account = CurrentAccountSyncData(
            instance_id=instance_id,
            db_type="oracle",
            username=username,
            oracle_roles=permissions_data.get("roles", []),
            system_privileges=permissions_data.get("system_privileges", []),
            tablespace_privileges_oracle=permissions_data.get("tablespace_privileges", []),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            last_change_type="add",
            session_id=session_id,
        )
        db.session.add(account)
        db.session.commit()
        return account

    @classmethod
    def _detect_mysql_changes(cls, account: CurrentAccountSyncData, new_permissions: dict) -> dict:
        """检测MySQL权限变更"""
        changes = {}

        # 检测全局权限变更
        old_global = set(account.global_privileges or [])
        new_global = set(new_permissions.get("global_privileges", []))
        if old_global != new_global:
            changes["global_privileges"] = {
                "added": list(new_global - old_global),
                "removed": list(old_global - new_global),
            }

        # 检测数据库权限变更
        old_db_perms = account.database_privileges or {}
        new_db_perms = new_permissions.get("database_privileges", {})
        if old_db_perms != new_db_perms:
            changes["database_privileges"] = {
                "added": {
                    k: v for k, v in new_db_perms.items() if k not in old_db_perms or set(old_db_perms[k]) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(new_db_perms.get(k, [])) != set(v)
                },
            }

        return changes

    @classmethod
    def _detect_postgresql_changes(cls, account: CurrentAccountSyncData, new_permissions: dict) -> dict:
        """检测PostgreSQL权限变更"""
        changes = {}

        # 检测预定义角色变更
        old_roles = set(account.predefined_roles or [])
        new_roles = set(new_permissions.get("predefined_roles", []))
        if old_roles != new_roles:
            changes["predefined_roles"] = {
                "added": list(new_roles - old_roles),
                "removed": list(old_roles - new_roles),
            }

        # 检测角色属性变更
        old_attrs = account.role_attributes or {}
        new_attrs = new_permissions.get("role_attributes", {})
        if old_attrs != new_attrs:
            changes["role_attributes"] = {
                "added": {k: v for k, v in new_attrs.items() if k not in old_attrs or old_attrs[k] != v},
                "removed": {k: v for k, v in old_attrs.items() if k not in new_attrs or new_attrs[k] != v},
            }

        # 检测数据库权限变更
        old_db_perms = account.database_privileges_pg or {}
        new_db_perms = new_permissions.get("database_privileges", {})
        if old_db_perms != new_db_perms:
            changes["database_privileges"] = {
                "added": {
                    k: v for k, v in new_db_perms.items() if k not in old_db_perms or set(old_db_perms[k]) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(new_db_perms.get(k, [])) != set(v)
                },
            }

        # 检测表空间权限变更
        old_tablespace_perms = account.tablespace_privileges or {}
        new_tablespace_perms = new_permissions.get("tablespace_privileges", {})
        if old_tablespace_perms != new_tablespace_perms:
            changes["tablespace_privileges"] = {
                "added": {
                    k: v
                    for k, v in new_tablespace_perms.items()
                    if k not in old_tablespace_perms or set(old_tablespace_perms[k]) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_tablespace_perms.items()
                    if k not in new_tablespace_perms or set(new_tablespace_perms.get(k, [])) != set(v)
                },
            }

        # 检测系统权限变更
        old_sys_perms = set(account.system_privileges or [])
        new_sys_perms = set(new_permissions.get("system_privileges", []))
        if old_sys_perms != new_sys_perms:
            changes["system_privileges"] = {
                "added": list(new_sys_perms - old_sys_perms),
                "removed": list(old_sys_perms - new_sys_perms),
            }

        return changes

    @classmethod
    def _detect_sqlserver_changes(cls, account: CurrentAccountSyncData, new_permissions: dict) -> dict:
        """检测SQL Server权限变更"""
        changes = {}

        # 检测服务器角色变更
        old_roles = set(account.server_roles or [])
        new_roles = set(new_permissions.get("server_roles", []))
        if old_roles != new_roles:
            changes["server_roles"] = {
                "added": list(new_roles - old_roles),
                "removed": list(old_roles - new_roles),
            }

        # 检测服务器权限变更
        old_perms = set(account.server_permissions or [])
        new_perms = set(new_permissions.get("server_permissions", []))
        if old_perms != new_perms:
            changes["server_permissions"] = {
                "added": list(new_perms - old_perms),
                "removed": list(old_perms - new_perms),
            }

        # 检测数据库角色变更
        old_db_roles = account.database_roles or {}
        new_db_roles = new_permissions.get("database_roles", {})
        if old_db_roles != new_db_roles:
            changes["database_roles"] = {
                "added": {
                    k: v for k, v in new_db_roles.items() if k not in old_db_roles or set(old_db_roles[k]) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_roles.items()
                    if k not in new_db_roles or set(new_db_roles.get(k, [])) != set(v)
                },
            }

        # 检测数据库权限变更
        old_db_perms = account.database_permissions or {}
        new_db_perms = new_permissions.get("database_permissions", {})
        if old_db_perms != new_db_perms:
            changes["database_permissions"] = {
                "added": {
                    k: v for k, v in new_db_perms.items() if k not in old_db_perms or set(old_db_perms[k]) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(new_db_perms.get(k, [])) != set(v)
                },
            }

        return changes

    @classmethod
    def _detect_oracle_changes(cls, account: CurrentAccountSyncData, new_permissions: dict) -> dict:
        """检测Oracle权限变更（移除表空间配额检测）"""
        changes = {}

        # 检测角色变更
        old_roles = set(account.oracle_roles or [])
        new_roles = set(new_permissions.get("roles", []))
        if old_roles != new_roles:
            changes["roles"] = {
                "added": list(new_roles - old_roles),
                "removed": list(old_roles - new_roles),
            }

        # 检测系统权限变更
        old_system_perms = set(account.system_privileges or [])
        new_system_perms = set(new_permissions.get("system_privileges", []))
        if old_system_perms != new_system_perms:
            changes["system_privileges"] = {
                "added": list(new_system_perms - old_system_perms),
                "removed": list(old_system_perms - new_system_perms),
            }

        # 检测表空间权限变更（移除表空间配额）
        old_tablespace_perms = set(account.tablespace_privileges_oracle or [])
        new_tablespace_perms = set(new_permissions.get("tablespace_privileges", []))
        if old_tablespace_perms != new_tablespace_perms:
            changes["tablespace_privileges"] = {
                "added": list(new_tablespace_perms - old_tablespace_perms),
                "removed": list(old_tablespace_perms - new_tablespace_perms),
            }

        return changes

    @classmethod
    def _update_mysql_account(cls, account: CurrentAccountSyncData, permissions_data: dict, is_superuser: bool):
        """更新MySQL账户数据"""
        account.global_privileges = permissions_data.get("global_privileges", [])
        account.database_privileges = permissions_data.get("database_privileges", {})
        account.type_specific = permissions_data.get("type_specific", {})
        account.is_superuser = is_superuser
        account.last_change_type = "modify_privilege"
        account.last_change_time = time_utils.now()
        account.last_sync_time = time_utils.now()
        db.session.commit()

    @classmethod
    def _update_postgresql_account(cls, account: CurrentAccountSyncData, permissions_data: dict, is_superuser: bool):
        """更新PostgreSQL账户数据"""
        account.predefined_roles = permissions_data.get("predefined_roles", [])
        account.role_attributes = permissions_data.get("role_attributes", {})
        account.database_privileges_pg = permissions_data.get("database_privileges", {})
        account.tablespace_privileges = permissions_data.get("tablespace_privileges", {})
        account.system_privileges = permissions_data.get("system_privileges", [])
        account.type_specific = permissions_data.get("type_specific", {})
        account.is_superuser = is_superuser
        account.last_change_type = "modify_privilege"
        account.last_change_time = time_utils.now()
        account.last_sync_time = time_utils.now()
        db.session.commit()

    @classmethod
    def _update_sqlserver_account(cls, account: CurrentAccountSyncData, permissions_data: dict, is_superuser: bool):
        """更新SQL Server账户数据"""
        account.server_roles = permissions_data.get("server_roles", [])
        account.server_permissions = permissions_data.get("server_permissions", [])
        account.database_roles = permissions_data.get("database_roles", {})
        account.database_permissions = permissions_data.get("database_permissions", {})
        account.type_specific = permissions_data.get("type_specific", {})
        account.is_superuser = is_superuser
        account.last_change_type = "modify_privilege"
        account.last_change_time = time_utils.now()
        account.last_sync_time = time_utils.now()
        db.session.commit()

    @classmethod
    def _update_oracle_account(cls, account: CurrentAccountSyncData, permissions_data: dict, is_superuser: bool):
        """更新Oracle账户数据"""
        account.oracle_roles = permissions_data.get("roles", [])
        account.system_privileges = permissions_data.get("system_privileges", [])
        account.tablespace_privileges_oracle = permissions_data.get("tablespace_privileges", [])
        account.type_specific = permissions_data.get("type_specific", {})
        account.is_superuser = is_superuser
        account.last_change_type = "modify_privilege"
        account.last_change_time = time_utils.now()
        account.last_sync_time = time_utils.now()
        db.session.commit()

    @classmethod
    def _log_changes(
        cls,
        instance_id: int,
        db_type: str,
        username: str,
        changes: dict,
        session_id: str = None,
    ):
        """记录权限变更日志"""
        # 生成详细的变更描述
        change_description = cls._generate_change_description(db_type, changes)

        change_log = AccountChangeLog(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            change_type="modify_privilege",
            session_id=session_id,
            privilege_diff=changes,
            message=change_description,
            status="success",
        )
        db.session.add(change_log)
        db.session.commit()

    @classmethod
    def _generate_change_description(cls, db_type: str, changes: dict) -> str:
        """生成变更描述"""
        descriptions = []

        if db_type == "mysql":
            descriptions.extend(cls._generate_mysql_change_description(changes))
        elif db_type == "postgresql":
            descriptions.extend(cls._generate_postgresql_change_description(changes))
        elif db_type == "sqlserver":
            descriptions.extend(cls._generate_sqlserver_change_description(changes))
        elif db_type == "oracle":
            descriptions.extend(cls._generate_oracle_change_description(changes))

        return "; ".join(descriptions) if descriptions else "权限已更新"

    @classmethod
    def _generate_mysql_change_description(cls, changes: dict) -> list[str]:
        """生成MySQL变更描述"""
        descriptions = []

        if "global_privileges" in changes:
            added = changes["global_privileges"].get("added", [])
            removed = changes["global_privileges"].get("removed", [])
            if added:
                descriptions.append(f"新增全局权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除全局权限: {', '.join(removed)}")

        if "database_privileges" in changes:
            added = changes["database_privileges"].get("added", {})
            removed = changes["database_privileges"].get("removed", {})
            if added:
                for db_name, perms in added.items():
                    descriptions.append(f"数据库 {db_name} 新增权限: {', '.join(perms)}")
            if removed:
                for db_name, perms in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除权限: {', '.join(perms)}")

        return descriptions

    @classmethod
    def _generate_postgresql_change_description(cls, changes: dict) -> list[str]:
        """生成PostgreSQL变更描述"""
        descriptions = []

        if "role_attributes" in changes:
            added = changes["role_attributes"].get("added", {})
            removed = changes["role_attributes"].get("removed", {})
            if added:
                if isinstance(added, dict):
                    for attr, value in added.items():
                        descriptions.append(f"角色属性 {attr}: {value}")
                elif isinstance(added, list):
                    descriptions.append(f"新增角色属性: {', '.join(added)}")
            if removed:
                if isinstance(removed, dict):
                    for attr, value in removed.items():
                        descriptions.append(f"移除角色属性 {attr}: {value}")
                elif isinstance(removed, list):
                    descriptions.append(f"移除角色属性: {', '.join(removed)}")

        if "predefined_roles" in changes:
            added = changes["predefined_roles"].get("added", [])
            removed = changes["predefined_roles"].get("removed", [])
            if added:
                descriptions.append(f"新增预定义角色: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除预定义角色: {', '.join(removed)}")

        if "database_privileges" in changes:
            added = changes["database_privileges"].get("added", {})
            removed = changes["database_privileges"].get("removed", {})
            if added:
                for db_name, perms in added.items():
                    descriptions.append(f"数据库 {db_name} 新增权限: {', '.join(perms)}")
            if removed:
                for db_name, perms in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除权限: {', '.join(perms)}")

        if "system_privileges" in changes:
            added = changes["system_privileges"].get("added", [])
            removed = changes["system_privileges"].get("removed", [])
            if added:
                descriptions.append(f"新增系统权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除系统权限: {', '.join(removed)}")

        return descriptions

    @classmethod
    def _generate_sqlserver_change_description(cls, changes: dict) -> list[str]:
        """生成SQL Server变更描述"""
        descriptions = []

        if "server_roles" in changes:
            added = changes["server_roles"].get("added", [])
            removed = changes["server_roles"].get("removed", [])
            if added:
                descriptions.append(f"新增服务器角色: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除服务器角色: {', '.join(removed)}")

        if "server_permissions" in changes:
            added = changes["server_permissions"].get("added", [])
            removed = changes["server_permissions"].get("removed", [])
            if added:
                descriptions.append(f"新增服务器权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除服务器权限: {', '.join(removed)}")

        if "database_roles" in changes:
            added = changes["database_roles"].get("added", {})
            removed = changes["database_roles"].get("removed", {})
            if added:
                for db_name, roles in added.items():
                    descriptions.append(f"数据库 {db_name} 新增角色: {', '.join(roles)}")
            if removed:
                for db_name, roles in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除角色: {', '.join(roles)}")

        if "database_permissions" in changes:
            added = changes["database_permissions"].get("added", {})
            removed = changes["database_permissions"].get("removed", {})
            if added:
                for db_name, perms in added.items():
                    descriptions.append(f"数据库 {db_name} 新增权限: {', '.join(perms)}")
            if removed:
                for db_name, perms in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除权限: {', '.join(perms)}")

        return descriptions

    @classmethod
    def _generate_oracle_change_description(cls, changes: dict) -> list[str]:
        """生成Oracle变更描述"""
        descriptions = []

        if "roles" in changes:
            added = changes["roles"].get("added", [])
            removed = changes["roles"].get("removed", [])
            if added:
                descriptions.append(f"新增Oracle角色: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除Oracle角色: {', '.join(removed)}")

        if "system_privileges" in changes:
            added = changes["system_privileges"].get("added", [])
            removed = changes["system_privileges"].get("removed", [])
            if added:
                descriptions.append(f"新增系统权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除系统权限: {', '.join(removed)}")

        if "tablespace_privileges" in changes:
            added = changes["tablespace_privileges"].get("added", [])
            removed = changes["tablespace_privileges"].get("removed", [])
            if added:
                descriptions.append(f"新增表空间权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除表空间权限: {', '.join(removed)}")

        return descriptions

    @classmethod
    def mark_account_deleted(cls, instance_id: int, db_type: str, username: str, session_id: str = None):
        """标记账户为已删除（不支持恢复）"""
        account = cls.get_account_latest(db_type, instance_id, username, include_deleted=True)
        if account and not account.is_deleted:
            account.is_deleted = True
            account.deleted_time = time_utils.now()
            account.last_change_type = "delete"
            account.last_change_time = time_utils.now()

            # 记录删除日志
            change_log = AccountChangeLog(
                instance_id=instance_id,
                db_type=db_type,
                username=username,
                change_type="delete",
                session_id=session_id,
                status="success",
            )
            db.session.add(change_log)
            db.session.commit()

    @classmethod
    def get_accounts_by_db_type(cls, db_type: str, include_deleted: bool = False) -> list[CurrentAccountSyncData]:
        """根据数据库类型获取账户列表"""
        query = CurrentAccountSyncData.query.filter_by(db_type=db_type)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()

    @classmethod
    def get_accounts_by_instance_and_db_type(
        cls, instance_id: int, db_type: str, include_deleted: bool = False
    ) -> list[CurrentAccountSyncData]:
        """根据实例ID和数据库类型获取账户列表"""
        query = CurrentAccountSyncData.query.filter_by(instance_id=instance_id, db_type=db_type)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()
