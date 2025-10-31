"""
鲸落 - SQL Server数据库同步适配器
处理SQL Server特定的账户同步逻辑

特性：
- 取消sysadmin特殊处理，所有账户获取实际权限
- 包含系统数据库权限查询，获取完整权限信息
- 支持服务器角色和数据库角色的精确检测
- 跨数据库权限查询和汇总
- 通过实际查询获取真实权限，避免硬编码假设
"""

# import signal  # 移除signal导入，避免在子线程中使用
import time
from typing import Any

from app.models import Instance
from app.constants import DatabaseType
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.services.cache_service import cache_manager
from app.services.connection_adapters.connection_factory import ConnectionFactory
from app.services.account_sync_filters.database_filter_manager import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.time_utils import time_utils

from .base_sync_adapter import BaseSyncAdapter

# 移除并行处理，改为顺序处理


class SQLServerSyncAdapter(BaseSyncAdapter):
    """SQL Server数据库同步适配器"""

    def __init__(self) -> None:
        super().__init__()
        self.filter_manager = DatabaseFilterManager()
        self._current_instance = None  # 当前处理的实例
        self.query_timeout = 5  # 查询超时5秒

    def _execute_query_with_timeout(self, connection: Any, sql: str, params: tuple = None) -> list:
        """
        执行带超时控制的查询
        
        Args:
            connection: 数据库连接对象
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        try:
            # 执行查询（移除signal超时控制，依赖连接工厂的超时机制）
            if params:
                result = connection.execute_query(sql, params)
            else:
                result = connection.execute_query(sql)
            
            return result
            
        except Exception as e:
            # 检查是否是超时相关的异常
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                self.sync_logger.warning(
                    "SQL Server查询超时",
                    module="sqlserver_sync_adapter",
                    instance_id=self._current_instance.id if self._current_instance else None,
                    sql=sql[:100],
                    timeout=self.query_timeout,
                    error=str(e)
                )
                raise TimeoutError(f"查询超时 ({self.query_timeout}秒): {sql[:100]}...")
            raise e

    def _quote_identifier(self, identifier: str) -> str:
        """
        转义SQL Server标识符，处理特殊字符

        Args:
            identifier: 需要转义的标识符

        Returns:
            转义后的标识符
        """
        if not identifier:
            return identifier

        # 如果已经包含方括号，直接返回
        if identifier.startswith("[") and identifier.endswith("]"):
            return identifier

        # 使用方括号转义标识符
        return f"[{identifier}]"

    def clear_user_cache(self, instance: Instance, username: str) -> bool:
        """清除用户缓存"""
        try:
            return cache_manager.invalidate_user_cache(instance.id, username)
        except Exception as e:
            self.sync_logger.error("清除用户缓存失败: %s", username, error=str(e))
            return False

    def clear_instance_cache(self, instance: Instance) -> bool:
        """清除实例缓存"""
        try:
            return cache_manager.invalidate_instance_cache(instance.id)
        except Exception as e:
            self.sync_logger.error("清除实例缓存失败: %s", instance.name, error=str(e))
            return False

    def get_database_accounts(self, instance: Instance, connection: Any) -> list[dict[str, Any]]:
        """
        获取SQL Server数据库中的所有账户信息 - 批量优化版本
        """
        try:
            # 设置当前实例
            self._current_instance = instance

            # 使用批量优化方法
            return self._get_database_accounts_batch(instance, connection)

        except Exception as e:
            self.sync_logger.error(
                "获取SQL Server登录失败", module="sqlserver_sync_adapter", instance_name=instance.name, error=str(e)
            )
            return []

    def _get_database_accounts_batch(self, instance: Instance, connection: Any) -> list[dict[str, Any]]:
        """
        批量获取SQL Server数据库中的所有账户信息 - 性能优化版本
        """
        try:
            start_time = time.time()

            # 构建安全的查询条件
            filter_conditions = self._build_filter_conditions()
            where_clause, params = filter_conditions

            # 1. 批量获取所有登录基本信息
            login_sql = f"""
                SELECT
                    sp.name as username,
                    sp.is_disabled as is_disabled,
                    sp.type_desc as login_type,
                    sp.type as type,
                    sp.create_date as create_date,
                    sp.modify_date as modify_date,
                    sp.sid as sid,
                    CASE
                        WHEN sp.type = 'S' THEN LOGINPROPERTY(sp.name, 'PasswordLastSetTime')
                        ELSE NULL
                    END as password_last_set_time,
                    CASE
                        WHEN sp.type = 'S' THEN sl.is_expiration_checked
                        ELSE NULL
                    END as is_expiration_checked,
                    CASE
                        WHEN sp.type = 'S' THEN sl.is_policy_checked
                        ELSE NULL
                    END as is_policy_checked
                FROM sys.server_principals sp
                LEFT JOIN sys.sql_logins sl ON sp.principal_id = sl.principal_id AND sp.type = 'S'
                WHERE sp.type IN ('S', 'U', 'G') AND {where_clause}
                ORDER BY sp.name
            """

            logins = self._execute_query_with_timeout(connection,login_sql, params)

            if not logins:
                return []

            # 2. 批量获取所有用户的服务器角色
            all_server_roles_sql = """
                SELECT p.name AS username, r.name AS role_name
                FROM sys.server_role_members rm
                JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
                WHERE p.type IN ('S', 'U', 'G')
                ORDER BY p.name, r.name
            """
            all_server_roles = self._execute_query_with_timeout(connection,all_server_roles_sql)
            server_roles_dict = {}
            for row in all_server_roles:
                username, role = row
                server_roles_dict.setdefault(username, []).append(role)

            # 3. 批量获取所有用户的服务器权限
            all_server_perms_sql = """
                SELECT sp.name AS username, perm.permission_name
                FROM sys.server_permissions perm
                JOIN sys.server_principals sp ON perm.grantee_principal_id = sp.principal_id
                WHERE sp.type IN ('S', 'U', 'G') AND perm.state = 'G'
                ORDER BY sp.name, perm.permission_name
            """
            all_server_perms = self._execute_query_with_timeout(connection,all_server_perms_sql)
            server_perms_dict = {}
            for row in all_server_perms:
                username, perm = row
                server_perms_dict.setdefault(username, []).append(perm)

            # 4. 批量获取所有用户的type_specific信息
            all_type_specific_sql = """
                SELECT
                    sp.name AS username,
                    sp.principal_id,
                    sp.is_disabled,
                    sp.type_desc,
                    sp.default_database_name,
                    sp.default_language_name,
                    CASE WHEN sp.type = 'S' THEN sl.is_expiration_checked ELSE NULL END as is_expiration_checked,
                    CASE WHEN sp.type = 'S' THEN sl.is_policy_checked ELSE NULL END as is_policy_checked
                FROM sys.server_principals sp
                LEFT JOIN sys.sql_logins sl ON sp.principal_id = sl.principal_id AND sp.type = 'S'
                WHERE sp.type IN ('S', 'U', 'G')
            """
            all_type_specific = self._execute_query_with_timeout(connection,all_type_specific_sql)
            type_specific_dict = {}
            for row in all_type_specific:
                username = row[0]
                type_specific_dict[username] = {
                    "principal_id": row[1],
                    "is_locked": row[2],
                    "account_type": row[3],
                    "default_database": row[4],
                    "default_language": row[5],
                    "is_expiration_checked": bool(row[6]) if row[6] is not None else None,
                    "is_policy_checked": bool(row[7]) if row[7] is not None else None,
                }

            # 5. 批量获取所有用户的数据库权限
            all_database_permissions = self._get_all_users_database_permissions_batch(
                connection, [row[0] for row in logins]
            )

            # 6. 构建账户数据
            accounts = []
            for login_row in logins:
                (
                    username,
                    is_disabled,
                    login_type,
                    type_code,
                    create_date,
                    modify_date,
                    sid,
                    password_last_set_time,
                    is_expiration_checked,
                    is_policy_checked,
                ) = login_row

                # 从批量数据中获取权限信息
                permissions = {
                    "server_roles": server_roles_dict.get(username, []),
                    "server_permissions": server_perms_dict.get(username, []),
                    "database_roles": all_database_permissions.get(username, {}).get("roles", {}),
                    "database_permissions": all_database_permissions.get(username, {}).get("permissions", {}),
                    "type_specific": type_specific_dict.get(username, {}),
                }

                # 判断是否为超级用户
                is_superuser = username.lower() == "sa" or "sysadmin" in permissions.get("server_roles", [])

                # 将锁定状态信息添加到type_specific中
                permissions["type_specific"]["is_disabled"] = is_disabled

                account_data = {
                    "username": username,
                    "is_superuser": is_superuser,
                    "is_disabled": is_disabled,
                    "login_type": login_type,
                    "type_code": type_code,
                    "create_date": create_date.isoformat() if create_date else None,
                    "modify_date": modify_date.isoformat() if modify_date else None,
                    "password_last_set_time": (
                        password_last_set_time.isoformat()
                        if password_last_set_time and hasattr(password_last_set_time, "isoformat")
                        else None
                    ),
                    "is_expiration_checked": bool(is_expiration_checked) if is_expiration_checked is not None else None,
                    "is_policy_checked": bool(is_policy_checked) if is_policy_checked is not None else None,
                    "permissions": permissions,
                }

                accounts.append(account_data)

            elapsed_time = time.time() - start_time
            self.sync_logger.info(
                "批量获取SQL Server登录完成",
                module="sqlserver_sync_adapter",
                instance_name=instance.name,
                account_count=len(accounts),
                elapsed_time=f"{elapsed_time:.2f}s",
            )

            return accounts

        except Exception as e:
            self.sync_logger.error(
                "批量获取SQL Server登录失败",
                module="sqlserver_sync_adapter",
                instance_name=instance.name,
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    def _build_filter_conditions(self) -> tuple[str, list]:
        """构建过滤条件"""
        filter_rules = self.filter_manager.get_filter_rules("sqlserver")

        # 使用数据库特定的SafeQueryBuilder
        builder = SafeQueryBuilder(db_type="sqlserver")

        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])

        # 使用统一的数据库特定条件构建方法
        builder.add_database_specific_condition("sp.name", exclude_users, exclude_patterns)

        return builder.build_where_clause()

    def extract_permissions(self, account_data: dict[str, Any]) -> dict[str, Any]:
        """从账户数据中提取权限信息"""
        return account_data.get("permissions", {})

    def format_account_data(self, raw_account: dict[str, Any]) -> dict[str, Any]:
        """格式化账户数据为统一格式"""
        permissions = raw_account.get("permissions", {})

        formatted_data = {
            "username": raw_account["username"],
            "is_superuser": raw_account.get("is_superuser", False),
            "permissions": {
                "server_roles": permissions.get("server_roles", []),
                "server_permissions": permissions.get("server_permissions", []),
                "database_roles": permissions.get("database_roles", {}),
                "database_permissions": permissions.get("database_permissions", {}),
                "type_specific": permissions.get("type_specific", {}),
            },
        }

        # 验证JSON可序列化性
        try:
            import json

            json.dumps(formatted_data["permissions"])
        except (TypeError, ValueError) as e:
            self.sync_logger.error("权限数据JSON序列化失败: %s", raw_account["username"], error=str(e))
            # 使用安全的默认值
            formatted_data["permissions"] = {
                "server_roles": [],
                "server_permissions": [],
                "database_roles": {},
                "database_permissions": {},
                "type_specific": {},
            }

        return formatted_data

    def _detect_changes(
        self, existing_account: CurrentAccountSyncData, new_permissions: dict[str, Any], *, is_superuser: bool
    ) -> dict[str, Any]:
        """检测SQL Server账户变更"""
        changes = {}

        # 检测超级用户状态变更
        if existing_account.is_superuser != is_superuser:
            changes["is_superuser"] = {"old": existing_account.is_superuser, "new": is_superuser}

        # 检测is_active状态变更（从type_specific中获取）
        new_is_active = new_permissions.get("type_specific", {}).get("is_active", False)
        if existing_account.is_active != new_is_active:
            changes["is_active"] = {"old": existing_account.is_active, "new": new_is_active}

        # 检测服务器角色变更
        old_roles = set(existing_account.server_roles or [])
        new_roles = set(new_permissions.get("server_roles", []))
        if old_roles != new_roles:
            changes["server_roles"] = {"added": list(new_roles - old_roles), "removed": list(old_roles - new_roles)}

        # 检测服务器权限变更
        old_perms = set(existing_account.server_permissions or [])
        new_perms = set(new_permissions.get("server_permissions", []))
        if old_perms != new_perms:
            changes["server_permissions"] = {
                "added": list(new_perms - old_perms),
                "removed": list(old_perms - new_perms),
            }

        # 检测数据库角色变更
        old_db_roles = existing_account.database_roles or {}
        new_db_roles = new_permissions.get("database_roles", {})

        # 使用集合比较，忽略顺序
        old_db_roles_set = {k: set(v) for k, v in old_db_roles.items()}
        new_db_roles_set = {k: set(v) for k, v in new_db_roles.items()}

        if old_db_roles_set != new_db_roles_set:
            changes["database_roles"] = {
                "added": {
                    k: v
                    for k, v in new_db_roles.items()
                    if k not in old_db_roles or set(old_db_roles.get(k, [])) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_roles.items()
                    if k not in new_db_roles or set(old_db_roles.get(k, [])) != set(new_db_roles.get(k, []))
                },
            }

        # 检测数据库权限变更
        old_db_perms = existing_account.database_permissions or {}
        new_db_perms = new_permissions.get("database_permissions", {})

        # 使用集合比较，忽略顺序
        old_db_perms_set = {k: set(v) for k, v in old_db_perms.items()}
        new_db_perms_set = {k: set(v) for k, v in new_db_perms.items()}

        if old_db_perms_set != new_db_perms_set:
            changes["database_permissions"] = {
                "added": {
                    k: v
                    for k, v in new_db_perms.items()
                    if k not in old_db_perms or set(old_db_perms.get(k, [])) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(old_db_perms.get(k, [])) != set(new_db_perms.get(k, []))
                },
            }

        # 检测type_specific字段变更
        old_type_specific = existing_account.type_specific or {}
        new_type_specific = new_permissions.get("type_specific", {})
        if old_type_specific != new_type_specific:
            changes["type_specific"] = {
                "added": {
                    k: v
                    for k, v in new_type_specific.items()
                    if k not in old_type_specific or old_type_specific[k] != v
                },
                "removed": {
                    k: v
                    for k, v in old_type_specific.items()
                    if k not in new_type_specific or new_type_specific[k] != v
                },
            }

        return changes

    def _update_account_permissions(
        self, account: CurrentAccountSyncData, permissions_data: dict[str, Any], *, is_superuser: bool
    ) -> None:
        """更新SQL Server账户权限信息"""
        try:
            account.server_roles = permissions_data.get("server_roles", [])
            account.server_permissions = permissions_data.get("server_permissions", [])
            account.database_roles = permissions_data.get("database_roles", {})
            account.database_permissions = permissions_data.get("database_permissions", {})
            account.type_specific = permissions_data.get("type_specific", {})
            account.is_superuser = is_superuser
            # 从type_specific中获取is_active状态
            account.is_active = permissions_data.get("type_specific", {}).get("is_active", False)
            account.is_deleted = False  # 重置删除状态
            account.deleted_time = None  # 清除删除时间
            account.last_change_type = "modify_privilege"
            account.last_change_time = time_utils.now()
            account.last_sync_time = time_utils.now()
        except Exception as e:
            self.sync_logger.error("更新SQL Server账户数据失败: %s", account.username, error=str(e))
            raise

    def _create_new_account(
        self,
        instance_id: int,
        db_type: str,
        username: str,
        permissions_data: dict[str, Any],
        is_superuser: bool,
        session_id: str,
    ) -> CurrentAccountSyncData:
        """创建新的SQL Server账户记录"""
        return CurrentAccountSyncData(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            server_roles=permissions_data.get("server_roles", []),
            server_permissions=permissions_data.get("server_permissions", []),
            database_roles=permissions_data.get("database_roles", {}),
            database_permissions=permissions_data.get("database_permissions", {}),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            # 从type_specific中获取is_active状态
            is_active=permissions_data.get("type_specific", {}).get("is_active", False),
            last_change_type="add",
            session_id=session_id,
        )

    def _generate_change_description(self, db_type: str, changes: dict[str, Any]) -> list[str]:
        """生成SQL Server账户变更描述"""
        descriptions = []

        if "is_superuser" in changes:
            new_value = changes["is_superuser"]["new"]
            if new_value:
                descriptions.append("提升为超级用户")
            else:
                descriptions.append("取消超级用户权限")

        if "server_roles" in changes:
            added = changes["server_roles"]["added"]
            removed = changes["server_roles"]["removed"]
            if added:
                descriptions.append(f"新增服务器角色: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除服务器角色: {', '.join(removed)}")

        if "server_permissions" in changes:
            added = changes["server_permissions"]["added"]
            removed = changes["server_permissions"]["removed"]
            if added:
                descriptions.append(f"新增服务器权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除服务器权限: {', '.join(removed)}")

        if "database_roles" in changes:
            added = changes["database_roles"]["added"]
            removed = changes["database_roles"]["removed"]
            if added:
                for db_name, roles in added.items():
                    descriptions.append(f"数据库 {db_name} 新增角色: {', '.join(roles)}")
            if removed:
                for db_name, roles in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除角色: {', '.join(roles)}")

        if "database_permissions" in changes:
            added = changes["database_permissions"]["added"]
            removed = changes["database_permissions"]["removed"]
            if added:
                for db_name, permissions in added.items():
                    descriptions.append(f"数据库 {db_name} 新增权限: {', '.join(permissions)}")
            if removed:
                for db_name, permissions in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除权限: {', '.join(permissions)}")

        if "type_specific" in changes:
            added = changes["type_specific"]["added"]
            removed = changes["type_specific"]["removed"]
            if added:
                descriptions.append(f"更新类型特定信息: {', '.join(added.keys())}")
            if removed:
                descriptions.append(f"移除类型特定信息: {', '.join(removed.keys())}")

        return descriptions

    def _get_all_users_database_permissions_batch(
        self, connection: Any, usernames: list[str]
    ) -> dict[str, dict[str, dict[str, list[str]]]]:
        """批量获取所有用户的数据库权限 - 性能优化版本"""
        try:
            start_time = time.time()

            # 获取数据库列表 - 包含系统数据库，获取更完整的权限信息
            databases_sql = """
                SELECT TOP 50 name
                FROM sys.databases
                WHERE state = 0
                AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """
            databases = self._execute_query_with_timeout(connection,databases_sql)

            if not databases:
                return {}

            database_list = [db[0] for db in databases]

            # 获取所有用户的SID映射
            usernames_str = "', '".join(usernames)
            login_sids_sql = f"""
                SELECT name, sid
                FROM sys.server_principals
                WHERE name IN ('{usernames_str}') AND type IN ('S', 'U', 'G')
            """
            login_sids = self._execute_query_with_timeout(connection,login_sids_sql)
            username_to_sid = {row[0]: row[1] for row in login_sids}

            # 移除sysadmin状态检查，不再需要特殊处理

            # 构建动态SQL获取所有数据库的principals
            principals_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                principals_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name,
                           principal_id,
                           sid
                    FROM {quoted_db}.sys.database_principals
                    WHERE type IN ('S', 'U', 'G') AND name != 'dbo'
                """
                )

            principals_sql = " UNION ALL ".join(principals_parts)
            all_principals = self._execute_query_with_timeout(connection,principals_sql)

            # 构建用户映射 {db: {user_name: (principal_id, sid)}}
            db_principals = {}
            for row in all_principals:
                db, user_name, pid, sid = row
                db_principals.setdefault(db, {})[user_name] = (pid, sid)

            # 构建动态SQL获取所有数据库的角色
            roles_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                roles_parts.append(
                    f"""
                    SELECT DISTINCT '{db}' AS db_name,
                           r.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name,
                           m.member_principal_id
                    FROM {quoted_db}.sys.database_role_members m
                    JOIN {quoted_db}.sys.database_principals r ON m.role_principal_id = r.principal_id
                """
                )

            roles_sql = " UNION ALL ".join(roles_parts)

            all_roles = self._execute_query_with_timeout(connection,roles_sql)

            # 构建动态SQL获取所有数据库的权限
            perms_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                perms_parts.append(
                    f"""
                    SELECT DISTINCT '{db}' AS db_name,
                           permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name,
                           grantee_principal_id,
                           major_id,
                           minor_id,
                           CASE 
                               WHEN major_id = 0 THEN 'DATABASE'
                               WHEN major_id > 0 AND minor_id = 0 THEN 'SCHEMA'
                               WHEN major_id > 0 AND minor_id > 0 THEN 'OBJECT'
                           END COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_scope,
                           CASE 
                               WHEN major_id = 0 THEN 'DATABASE'
                               WHEN major_id > 0 AND minor_id = 0 THEN 
                                   (SELECT name FROM {quoted_db}.sys.schemas WHERE schema_id = major_id)
                               WHEN major_id > 0 AND minor_id > 0 THEN 
                                   (SELECT name FROM {quoted_db}.sys.objects WHERE object_id = major_id)
                           END COLLATE SQL_Latin1_General_CP1_CI_AS AS object_name
                    FROM {quoted_db}.sys.database_permissions WHERE state = 'G'
                """
                )

            perms_sql = " UNION ALL ".join(perms_parts)

            all_perms = self._execute_query_with_timeout(connection,perms_sql)

            # 在Python中聚合数据
            result = {}
            for username in usernames:
                result[username] = {"roles": {}, "permissions": {}}

            # 处理角色
            for row in all_roles:
                db_name, role_name, member_principal_id = row

                # 查找对应的用户名
                user_name = None
                for u_name, (pid, _) in db_principals.get(db_name, {}).items():
                    if pid == member_principal_id:
                        user_name = u_name
                        break

                # 确定匹配的用户名（优先用户名匹配，然后SID匹配）
                matched_username = None
                if user_name in usernames:
                    matched_username = user_name
                else:
                    # 通过SID匹配
                    for username, sid in username_to_sid.items():
                        if sid and any(
                            sid == db_sid
                            for _, (_, db_sid) in db_principals.get(db_name, {}).items()
                            if pid == member_principal_id
                        ):
                            matched_username = username
                            break

                # 只添加一次，避免重复
                if matched_username:
                    if db_name not in result[matched_username]["roles"]:
                        result[matched_username]["roles"][db_name] = []
                    # 避免重复添加相同的角色
                    if role_name not in result[matched_username]["roles"][db_name]:
                        result[matched_username]["roles"][db_name].append(role_name)
                        # 调试日志
                        self.sync_logger.debug(
                            "添加角色: %s -> %s.%s",
                            matched_username,
                            db_name,
                            role_name,
                            module="sqlserver_sync_adapter"
                        )

            # 处理权限 - 按权限作用范围分类存储
            for row in all_perms:
                db_name, permission_name, grantee_principal_id, major_id, minor_id, scope, object_name = row

                # 查找对应的用户名
                user_name = None
                for u_name, (pid, _) in db_principals.get(db_name, {}).items():
                    if pid == grantee_principal_id:
                        user_name = u_name
                        break

                # 确定匹配的用户名（优先用户名匹配，然后SID匹配）
                matched_username = None
                if user_name in usernames:
                    matched_username = user_name
                else:
                    # 通过SID匹配
                    for username, sid in username_to_sid.items():
                        if sid and any(
                            sid == db_sid
                            for _, (_, db_sid) in db_principals.get(db_name, {}).items()
                            if pid == grantee_principal_id
                        ):
                            matched_username = username
                            break

                # 只添加一次，避免重复
                if matched_username:
                    if db_name not in result[matched_username]["permissions"]:
                        result[matched_username]["permissions"][db_name] = {
                            "database": [],
                            "schema": {},
                            "table": {}
                        }
                    
                    # 根据权限作用范围分类存储
                    if scope == "DATABASE":
                        if permission_name not in result[matched_username]["permissions"][db_name]["database"]:
                            result[matched_username]["permissions"][db_name]["database"].append(permission_name)
                    elif scope == "SCHEMA":
                        schema_name = object_name
                        if schema_name not in result[matched_username]["permissions"][db_name]["schema"]:
                            result[matched_username]["permissions"][db_name]["schema"][schema_name] = []
                        if permission_name not in result[matched_username]["permissions"][db_name]["schema"][schema_name]:
                            result[matched_username]["permissions"][db_name]["schema"][schema_name].append(permission_name)
                    elif scope == "OBJECT":
                        table_name = object_name
                        if table_name not in result[matched_username]["permissions"][db_name]["table"]:
                            result[matched_username]["permissions"][db_name]["table"][table_name] = []
                        if permission_name not in result[matched_username]["permissions"][db_name]["table"][table_name]:
                            result[matched_username]["permissions"][db_name]["table"][table_name].append(permission_name)

            # 移除sysadmin特殊处理，让系统通过实际查询获取真实权限
            # 这样可以获取更准确的权限信息，而不是硬编码添加db_owner角色

            # 排序结果
            for username in result:
                for db_name in result[username]["roles"]:
                    result[username]["roles"][db_name].sort()
                for db_name in result[username]["permissions"]:
                    # 排序数据库级别权限
                    result[username]["permissions"][db_name]["database"].sort()
                    # 排序架构级别权限
                    for schema_name in result[username]["permissions"][db_name]["schema"]:
                        result[username]["permissions"][db_name]["schema"][schema_name].sort()
                    # 排序表级别权限
                    for table_name in result[username]["permissions"][db_name]["table"]:
                        result[username]["permissions"][db_name]["table"][table_name].sort()

            elapsed_time = time.time() - start_time
            self.sync_logger.info(
                "批量获取所有用户数据库权限完成",
                module="sqlserver_sync_adapter",
                user_count=len(usernames),
                database_count=len(database_list),
                elapsed_time=f"{elapsed_time:.2f}s",
            )

            return result

        except Exception as e:
            self.sync_logger.error(
                "批量获取所有用户数据库权限失败",
                module="sqlserver_sync_adapter",
                error=str(e),
                error_type=type(e).__name__,
            )
            return {}
