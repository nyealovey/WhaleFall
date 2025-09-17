"""
泰摸鱼吧 - SQL Server数据库同步适配器
处理SQL Server特定的账户同步逻辑

特性：
- 取消sysadmin特殊处理，所有账户获取实际权限
- 支持服务器角色和数据库角色的精确检测
- 智能处理sysadmin用户的dbo权限映射
- 跨数据库权限查询和汇总
"""

from typing import Any, Dict, List, Tuple
import time
# 移除并行处理，改为顺序处理

from app.models import Instance
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.services.database_filter_manager import DatabaseFilterManager
from app.services.connection_factory import ConnectionFactory
from app.services.cache_manager import cache_manager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.time_utils import time_utils

from .base_sync_adapter import BaseSyncAdapter


class SQLServerSyncAdapter(BaseSyncAdapter):
    """SQL Server数据库同步适配器"""

    def __init__(self):
        super().__init__()
        self.filter_manager = DatabaseFilterManager()
        self._current_instance = None  # 当前处理的实例

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
        if identifier.startswith('[') and identifier.endswith(']'):
            return identifier
        
        # 使用方括号转义标识符
        return f"[{identifier}]"
    
    def clear_user_cache(self, instance: Instance, username: str) -> bool:
        """清除用户缓存"""
        try:
            return cache_manager.invalidate_user_cache(instance.id, username)
        except Exception as e:
            self.sync_logger.error(f"清除用户缓存失败: {username}", error=str(e))
            return False
    
    def clear_instance_cache(self, instance: Instance) -> bool:
        """清除实例缓存"""
        try:
            return cache_manager.invalidate_instance_cache(instance.id)
        except Exception as e:
            self.sync_logger.error(f"清除实例缓存失败: {instance.name}", error=str(e))
            return False

    def get_database_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:
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
                "获取SQL Server登录失败",
                module="sqlserver_sync_adapter",
                instance_name=instance.name,
                error=str(e)
            )
            return []

    def _get_database_accounts_batch(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:
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

            logins = connection.execute_query(login_sql, params)
            
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
            all_server_roles = connection.execute_query(all_server_roles_sql)
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
            all_server_perms = connection.execute_query(all_server_perms_sql)
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
            all_type_specific = connection.execute_query(all_type_specific_sql)
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
                    "is_policy_checked": bool(row[7]) if row[7] is not None else None
                }

            # 5. 批量获取所有用户的数据库权限
            all_database_permissions = self._get_all_users_database_permissions_batch(connection, [row[0] for row in logins])

            # 6. 构建账户数据
            accounts = []
            for login_row in logins:
                (username, is_disabled, login_type, type_code, create_date, modify_date,
                 sid, password_last_set_time, is_expiration_checked, is_policy_checked) = login_row
                
                # 从批量数据中获取权限信息
                permissions = {
                    "server_roles": server_roles_dict.get(username, []),
                    "server_permissions": server_perms_dict.get(username, []),
                    "database_roles": all_database_permissions.get(username, {}).get("roles", {}),
                    "database_permissions": all_database_permissions.get(username, {}).get("permissions", {}),
                    "type_specific": type_specific_dict.get(username, {})
                }
                
                # 判断是否为超级用户
                is_superuser = username.lower() == "sa" or "sysadmin" in permissions.get("server_roles", [])
                
                account_data = {
                    "username": username,
                    "is_superuser": is_superuser,
                    "is_active": not is_disabled,  # SQL Server: !is_disabled决定激活状态
                    "is_disabled": is_disabled,
                    "login_type": login_type,
                    "type_code": type_code,
                    "create_date": create_date.isoformat() if create_date else None,
                    "modify_date": modify_date.isoformat() if modify_date else None,
                    "password_last_set_time": password_last_set_time.isoformat() if password_last_set_time and hasattr(password_last_set_time, 'isoformat') else None,
                    "is_expiration_checked": bool(is_expiration_checked) if is_expiration_checked is not None else None,
                    "is_policy_checked": bool(is_policy_checked) if is_policy_checked is not None else None,
                    "permissions": permissions
                }
                
                accounts.append(account_data)

            elapsed_time = time.time() - start_time
            self.sync_logger.info(
                f"批量获取SQL Server登录完成",
                module="sqlserver_sync_adapter",
                instance_name=instance.name,
                account_count=len(accounts),
                elapsed_time=f"{elapsed_time:.2f}s"
            )

            return accounts

        except Exception as e:
            self.sync_logger.error(
                "批量获取SQL Server登录失败",
                module="sqlserver_sync_adapter",
                instance_name=instance.name,
                error=str(e),
                error_type=type(e).__name__
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

    def _get_login_permissions(self, connection: Any, username: str) -> Dict[str, Any]:
        """
        获取SQL Server登录的详细权限信息
        """
        try:
            permissions = {
                "server_roles": [],
                "server_permissions": [],
                "database_roles": {},
                "database_permissions": {},
                "type_specific": {}
            }

            # 获取服务器角色
            server_roles = self._get_server_roles(connection, username)
            permissions["server_roles"] = server_roles

            # 获取服务器权限
            server_permissions = self._get_server_permissions(connection, username)
            permissions["server_permissions"] = server_permissions

            # 获取数据库角色和权限 - 所有用户都获取实际权限
            self.sync_logger.debug(
                f"开始获取用户实际数据库权限: {username}",
                module="sqlserver_sync_adapter",
                username=username,
                server_roles=server_roles
            )
            
            database_roles, database_permissions = self._get_regular_database_permissions(connection, username)
            
            self.sync_logger.debug(
                f"用户数据库权限获取完成: {username}",
                module="sqlserver_sync_adapter",
                username=username,
                database_count=len(database_roles),
                databases_with_roles=list(database_roles.keys()),
                databases_with_permissions=list(database_permissions.keys())
            )

            permissions["database_roles"] = database_roles
            permissions["database_permissions"] = database_permissions

            # 获取特定信息
            type_specific = self._get_type_specific_info(connection, username)
            permissions["type_specific"] = type_specific

            return permissions

        except Exception as e:
            self.sync_logger.error(
                f"获取SQL Server登录权限失败: {username}",
                module="sqlserver_sync_adapter",
                error=str(e)
            )
            return {
                "server_roles": [],
                "server_permissions": [],
                "database_roles": {},
                "database_permissions": {},
                "type_specific": {}
            }

    def _get_server_roles(self, connection: Any, username: str) -> List[str]:
        """获取服务器角色"""
        try:
            sql = """
                SELECT r.name
                FROM sys.server_role_members rm
                JOIN sys.server_principals r ON rm.role_principal_id = r.principal_id
                JOIN sys.server_principals p ON rm.member_principal_id = p.principal_id
                WHERE p.name = %s
                ORDER BY r.name
            """
            result = connection.execute_query(sql, (username,))
            roles = [row[0] for row in result] if result else []
            return roles
        except Exception as e:
            self.sync_logger.error(f"获取服务器角色失败: {username}", error=str(e), sql=sql)
            return []

    def _get_server_permissions(self, connection: Any, username: str) -> List[str]:
        """获取服务器权限"""
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
                ORDER BY permission_name
            """
            result = connection.execute_query(sql, (username,))
            return [row[0] for row in result] if result else []
        except Exception as e:
            self.sync_logger.warning(f"获取服务器权限失败: {username}", error=str(e), sql=sql)
            return []

    def _get_regular_database_permissions(self, connection: Any, username: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """获取用户的实际数据库权限 - 批量优化版本"""
        # 使用新的批量方法
        return self._get_all_database_permissions_batch(connection, username)
    
    def _get_regular_database_permissions_old(self, connection: Any, username: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """获取用户的实际数据库权限 - 并行优化+缓存版本（旧版本）"""
        try:
            start_time = time.time()
            
            # 获取所有在线数据库
            databases_sql = """
                SELECT name 
                FROM sys.databases 
                WHERE state = 0 
                AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
                AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """
            databases = connection.execute_query(databases_sql)

            if not databases:
                return {}, {}

            # 限制处理的数据库数量，避免超时
            max_databases = 50
            database_list = [db[0] for db in databases[:max_databases]]
            
            if len(databases) > max_databases:
                self.sync_logger.warning(
                    f"数据库数量({len(databases)})超过限制({max_databases})，只处理前{max_databases}个: {username}",
                    module="sqlserver_sync_adapter"
                )

            # 尝试从缓存获取所有数据库权限
            instance_id = self._current_instance.id if self._current_instance else 0
            cached_permissions = cache_manager.get_all_database_permissions_cache(instance_id, username)
            
            database_roles = {}
            database_permissions = {}
            uncached_databases = []
            
            if cached_permissions:
                # 检查哪些数据库有缓存
                for db_name in database_list:
                    if db_name in cached_permissions:
                        roles, perms = cached_permissions[db_name]
                        if roles:
                            database_roles[db_name] = roles
                        if perms:
                            database_permissions[db_name] = perms
                    else:
                        uncached_databases.append(db_name)
                
                self.sync_logger.info(
                    f"缓存命中统计: {username}",
                    cached_count=len(database_list) - len(uncached_databases),
                    uncached_count=len(uncached_databases),
                    module="sqlserver_sync_adapter"
                )
            else:
                # 没有缓存，处理所有数据库
                uncached_databases = database_list

            def process_database(db_name: str) -> Tuple[str, List[str], List[str]]:
                """处理单个数据库的权限查询"""
                try:
                    # 创建独立连接
                    if not self._current_instance:
                        self.sync_logger.error("当前实例未设置，无法创建独立连接")
                        return db_name, [], []
                    
                    conn = ConnectionFactory.create_connection(self._current_instance)
                    conn.connect()
                    
                    # 确保连接已正确建立
                    if not hasattr(conn, 'connection') or conn.connection is None:
                        self.sync_logger.warning(f"连接未正确建立，跳过数据库: {db_name}")
                        return db_name, [], []
                    
                    try:
                        # 切换到目标数据库
                        use_db_sql = f"USE {self._quote_identifier(db_name)}"
                        conn.execute_query(use_db_sql)
                        
                        # 检查用户是否存在
                        user_exists_sql = """
                            SELECT principal_id, name, type_desc
                            FROM sys.database_principals
                            WHERE name = %s
                        """
                        user_info = conn.execute_query(user_exists_sql, (username,))
                        
                        if user_info:
                            # 用户存在，使用其principal_id
                            user_principal_id = user_info[0][0]
                        else:
                            # 检查是否sysadmin
                            sysadmin_check_sql = """
                                SELECT IS_SRVROLEMEMBER('sysadmin', %s) as is_sysadmin
                            """
                            sysadmin_result = conn.execute_query(sysadmin_check_sql, (username,))
                            if sysadmin_result and sysadmin_result[0][0] == 1:
                                user_principal_id = 1  # dbo
                            else:
                                return db_name, [], []  # 非sysadmin且不存在，跳过
                        
                        # 获取数据库角色
                        roles_sql = """
                            SELECT r.name
                            FROM sys.database_role_members rm
                            JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
                            WHERE rm.member_principal_id = %s
                            ORDER BY r.name
                        """
                        
                        roles = conn.execute_query(roles_sql, (user_principal_id,))
                        roles_list = [role[0] for role in roles] if roles else []
                        
                        # 对于sysadmin用户使用dbo权限时，添加db_owner角色
                        if user_principal_id == 1 and 'db_owner' not in roles_list:
                            roles_list.append('db_owner')
                        
                        # 获取数据库权限
                        perms_sql = """
                            SELECT permission_name
                            FROM sys.database_permissions
                            WHERE grantee_principal_id = %s
                            AND state = 'G'
                            ORDER BY permission_name
                        """
                        
                        permissions = conn.execute_query(perms_sql, (user_principal_id,))
                        perms_list = [perm[0] for perm in permissions] if permissions else []
                        
                        return db_name, roles_list, perms_list
                        
                    finally:
                        conn.close()
                        
                except Exception as e:
                    self.sync_logger.warning(
                        f"处理数据库 {db_name} 失败: {str(e)}",
                        module="sqlserver_sync_adapter",
                        username=username,
                        database=db_name,
                        error_type=type(e).__name__
                    )
                    return db_name, [], []

            # 顺序处理未缓存的数据库
            if uncached_databases:
                failed_count = 0
                
                for db_name in uncached_databases:
                    try:
                        db_name, roles_list, perms_list = process_database(db_name)
                        
                        if roles_list:
                            database_roles[db_name] = roles_list
                        if perms_list:
                            database_permissions[db_name] = perms_list
                        
                        # 设置缓存
                        cache_manager.set_database_permissions_cache(
                            instance_id, username, db_name, roles_list, perms_list
                        )
                            
                    except Exception as e:
                        failed_count += 1
                        self.sync_logger.warning(
                            f"处理数据库 {db_name} 失败: {str(e)}",
                            module="sqlserver_sync_adapter"
                        )
            else:
                failed_count = 0

            # 记录性能统计
            duration = time.time() - start_time
            processed_count = len(uncached_databases) - failed_count if uncached_databases else 0
            cached_count = len(database_list) - len(uncached_databases)
            
            self.sync_logger.info(
                f"并行数据库权限查询完成: {username}",
                duration=f"{duration:.2f}秒",
                total_databases=len(database_list),
                cached_count=cached_count,
                processed_count=processed_count,
                failed_count=failed_count,
                cache_hit_rate=f"{(cached_count/len(database_list)*100):.1f}%" if database_list else "0%",
                databases_per_second=f"{len(uncached_databases)/duration:.2f}" if uncached_databases and duration > 0 else "N/A",
                module="sqlserver_sync_adapter"
            )

            return database_roles, database_permissions

        except Exception as e:
            self.sync_logger.error(f"获取数据库权限失败: {username}", error=str(e), databases_sql=databases_sql)
            return {}, {}


    def _get_type_specific_info(self, connection: Any, username: str) -> Dict[str, Any]:
        """获取SQL Server特定信息"""
        try:
            # 获取登录的详细信息
            sql = """
                SELECT
                    sp.principal_id,
                    sp.is_disabled,
                    sp.type_desc,
                    sp.default_database_name,
                    sp.default_language_name,
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
                WHERE sp.name = %s
            """
            
            result = connection.execute_query(sql, (username,))
            
            if result:
                (principal_id, is_disabled, type_desc, default_database, default_language,
                 is_expiration_checked, is_policy_checked) = result[0]
                
                return {
                    "principal_id": principal_id,
                    "is_locked": is_disabled,  # SQL Server的is_disabled映射到is_locked
                    "account_type": type_desc,
                    "default_database": default_database,
                    "default_language": default_language,
                    "is_expiration_checked": bool(is_expiration_checked) if is_expiration_checked is not None else None,
                    "is_policy_checked": bool(is_policy_checked) if is_policy_checked is not None else None
                }
            return {}
        except Exception as e:
            self.sync_logger.warning(f"获取特定信息失败: {username}", error=str(e), sql=sql)
            return {}

    def extract_permissions(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """从账户数据中提取权限信息"""
        return account_data.get("permissions", {})

    def format_account_data(self, raw_account: Dict[str, Any]) -> Dict[str, Any]:
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
                "type_specific": permissions.get("type_specific", {})
            }
        }
        
        # 验证JSON可序列化性
        try:
            import json
            json.dumps(formatted_data["permissions"])
        except (TypeError, ValueError) as e:
            self.sync_logger.error(
                f"权限数据JSON序列化失败: {raw_account['username']}",
                error=str(e)
            )
            # 使用安全的默认值
            formatted_data["permissions"] = {
                "server_roles": [],
                "server_permissions": [],
                "database_roles": {},
                "database_permissions": {},
                "type_specific": {}
            }
        
        return formatted_data

    def _detect_changes(self, existing_account: CurrentAccountSyncData, 
                       new_permissions: Dict[str, Any], is_superuser: bool) -> Dict[str, Any]:
        """检测SQL Server账户变更"""
        changes = {}

        # 检测超级用户状态变更
        if existing_account.is_superuser != is_superuser:
            changes["is_superuser"] = {
                "old": existing_account.is_superuser,
                "new": is_superuser
            }

        # 检测服务器角色变更
        old_roles = set(existing_account.server_roles or [])
        new_roles = set(new_permissions.get("server_roles", []))
        if old_roles != new_roles:
            changes["server_roles"] = {
                "added": list(new_roles - old_roles),
                "removed": list(old_roles - new_roles)
            }

        # 检测服务器权限变更
        old_perms = set(existing_account.server_permissions or [])
        new_perms = set(new_permissions.get("server_permissions", []))
        if old_perms != new_perms:
            changes["server_permissions"] = {
                "added": list(new_perms - old_perms),
                "removed": list(old_perms - new_perms)
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
                    k: v for k, v in new_db_roles.items() 
                    if k not in old_db_roles or set(old_db_roles.get(k, [])) != set(v)
                },
                "removed": {
                    k: v for k, v in old_db_roles.items()
                    if k not in new_db_roles or set(old_db_roles.get(k, [])) != set(new_db_roles.get(k, []))
                }
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
                    k: v for k, v in new_db_perms.items() 
                    if k not in old_db_perms or set(old_db_perms.get(k, [])) != set(v)
                },
                "removed": {
                    k: v for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(old_db_perms.get(k, [])) != set(new_db_perms.get(k, []))
                }
            }

        # 检测type_specific字段变更
        old_type_specific = existing_account.type_specific or {}
        new_type_specific = new_permissions.get("type_specific", {})
        if old_type_specific != new_type_specific:
            changes["type_specific"] = {
                "added": {k: v for k, v in new_type_specific.items() 
                         if k not in old_type_specific or old_type_specific[k] != v},
                "removed": {k: v for k, v in old_type_specific.items() 
                           if k not in new_type_specific or new_type_specific[k] != v}
            }

        return changes

    def _update_account_permissions(self, account: CurrentAccountSyncData, 
                                   permissions_data: Dict[str, Any], is_superuser: bool, is_active: bool = None) -> None:
        """更新SQL Server账户权限信息"""
        try:
            account.server_roles = permissions_data.get("server_roles", [])
            account.server_permissions = permissions_data.get("server_permissions", [])
            account.database_roles = permissions_data.get("database_roles", {})
            account.database_permissions = permissions_data.get("database_permissions", {})
            account.type_specific = permissions_data.get("type_specific", {})
            account.is_superuser = is_superuser
            if is_active is not None:
                account.is_active = is_active
            account.is_deleted = False  # 重置删除状态
            account.deleted_time = None  # 清除删除时间
            account.last_change_type = "modify_privilege"
            account.last_change_time = time_utils.now()
            account.last_sync_time = time_utils.now()
        except Exception as e:
            self.sync_logger.error(f"更新SQL Server账户数据失败: {account.username}", error=str(e))
            raise

    def _create_new_account(self, instance_id: int, db_type: str, username: str,
                           permissions_data: Dict[str, Any], is_superuser: bool,
                           session_id: str, is_active: bool = True) -> CurrentAccountSyncData:
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
            is_active=is_active,
            last_change_type="add",
            session_id=session_id
        )

    def _generate_change_description(self, db_type: str, changes: Dict[str, Any]) -> List[str]:
        """生成SQL Server账户变更描述"""
        descriptions = []
        
        if "is_superuser" in changes:
            old_value = changes["is_superuser"]["old"]
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

    def _get_all_database_permissions_batch(self, connection: Any, username: str) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        """批量获取用户数据库权限 - 性能优化版本"""
        try:
            start_time = time.time()
            
            # 获取数据库列表
            databases_sql = """
                SELECT TOP 50 name 
                FROM sys.databases 
                WHERE state = 0 
                AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
                AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """
            databases = connection.execute_query(databases_sql)
            
            if not databases:
                return {}, {}
            
            database_list = [db[0] for db in databases]
            
            # 检查用户是否为sysadmin
            sysadmin_check_sql = """
                SELECT IS_SRVROLEMEMBER('sysadmin', %s) as is_sysadmin
            """
            sysadmin_result = connection.execute_query(sysadmin_check_sql, (username,))
            is_sysadmin = sysadmin_result and sysadmin_result[0][0] == 1
            
            # 构建动态SQL获取所有数据库的principals
            principals_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                principals_parts.append(f"""
                    SELECT '{db}' AS db_name, 
                           name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name, 
                           principal_id, 
                           sid 
                    FROM {quoted_db}.sys.database_principals 
                    WHERE type IN ('S', 'U', 'G') AND name != 'dbo'
                """)
            
            principals_sql = " UNION ALL ".join(principals_parts)
            
            all_principals = connection.execute_query(principals_sql)
            
            # 构建用户映射 {db: {user_name: (principal_id, sid)}}
            db_principals = {}
            for row in all_principals:
                db, user_name, pid, sid = row
                db_principals.setdefault(db, {})[user_name] = (pid, sid)
            
            # 构建动态SQL获取所有数据库的角色
            roles_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                roles_parts.append(f"""
                    SELECT '{db}' AS db_name, 
                           r.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name, 
                           m.member_principal_id 
                    FROM {quoted_db}.sys.database_role_members m
                    JOIN {quoted_db}.sys.database_principals r ON m.role_principal_id = r.principal_id
                """)
            
            roles_sql = " UNION ALL ".join(roles_parts)
            
            all_roles = connection.execute_query(roles_sql)
            
            # 构建动态SQL获取所有数据库的权限
            perms_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                perms_parts.append(f"""
                    SELECT '{db}' AS db_name, 
                           permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name, 
                           grantee_principal_id 
                    FROM {quoted_db}.sys.database_permissions WHERE state = 'G'
                """)
            
            perms_sql = " UNION ALL ".join(perms_parts)
            
            all_perms = connection.execute_query(perms_sql)
            
            # 获取服务器登录的SID用于映射
            login_sid_sql = """
                SELECT name, sid 
                FROM sys.server_principals 
                WHERE name = %s AND type IN ('S', 'U', 'G')
            """
            login_info = connection.execute_query(login_sid_sql, (username,))
            login_sid = login_info[0][1] if login_info else None
            
            # 在Python中聚合数据
            database_roles = {}
            database_permissions = {}
            
            # 处理角色
            for row in all_roles:
                db_name, role_name, member_principal_id = row
                
                # 查找对应的用户名
                user_name = None
                for u_name, (pid, sid) in db_principals.get(db_name, {}).items():
                    if pid == member_principal_id:
                        user_name = u_name
                        break
                
                # 如果找到用户名且匹配当前用户，或者通过SID匹配
                if user_name == username or (login_sid and any(sid == login_sid for _, (_, sid) in db_principals.get(db_name, {}).items() if pid == member_principal_id)):
                    if db_name not in database_roles:
                        database_roles[db_name] = []
                    database_roles[db_name].append(role_name)
            
            # 处理权限
            for row in all_perms:
                db_name, permission_name, grantee_principal_id = row
                
                # 查找对应的用户名
                user_name = None
                for u_name, (pid, sid) in db_principals.get(db_name, {}).items():
                    if pid == grantee_principal_id:
                        user_name = u_name
                        break
                
                # 如果找到用户名且匹配当前用户，或者通过SID匹配
                if user_name == username or (login_sid and any(sid == login_sid for _, (_, sid) in db_principals.get(db_name, {}).items() if pid == grantee_principal_id)):
                    if db_name not in database_permissions:
                        database_permissions[db_name] = []
                    database_permissions[db_name].append(permission_name)
            
            # 对于sysadmin用户，添加db_owner角色到所有数据库
            if is_sysadmin:
                for db_name in database_list:
                    if db_name not in database_roles:
                        database_roles[db_name] = []
                    if 'db_owner' not in database_roles[db_name]:
                        database_roles[db_name].append('db_owner')
            
            # 排序结果
            for db_name in database_roles:
                database_roles[db_name].sort()
            for db_name in database_permissions:
                database_permissions[db_name].sort()
            
            elapsed_time = time.time() - start_time
            self.sync_logger.info(
                f"批量获取数据库权限完成: {username}",
                module="sqlserver_sync_adapter",
                username=username,
                database_count=len(database_list),
                roles_count=sum(len(roles) for roles in database_roles.values()),
                permissions_count=sum(len(perms) for perms in database_permissions.values()),
                elapsed_time=f"{elapsed_time:.2f}s"
            )
            
            return database_roles, database_permissions
            
        except Exception as e:
            self.sync_logger.error(
                f"批量获取数据库权限失败: {username}",
                module="sqlserver_sync_adapter",
                username=username,
                error=str(e),
                error_type=type(e).__name__
            )
            return {}, {}

    def _get_all_users_database_permissions_batch(self, connection: Any, usernames: List[str]) -> Dict[str, Dict[str, Dict[str, List[str]]]]:
        """批量获取所有用户的数据库权限 - 性能优化版本"""
        try:
            start_time = time.time()
            
            # 获取数据库列表
            databases_sql = """
                SELECT TOP 50 name 
                FROM sys.databases 
                WHERE state = 0 
                AND name NOT IN ('master', 'tempdb', 'model', 'msdb')
                AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """
            databases = connection.execute_query(databases_sql)
            
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
            login_sids = connection.execute_query(login_sids_sql)
            username_to_sid = {row[0]: row[1] for row in login_sids}
            
            # 批量检查所有用户的sysadmin状态
            usernames_placeholders = ', '.join(['%s'] * len(usernames))
            sysadmin_check_sql = f"""
                SELECT sp.name, IS_SRVROLEMEMBER('sysadmin', sp.name) as is_sysadmin
                FROM sys.server_principals sp
                WHERE sp.name IN ({usernames_placeholders})
            """
            sysadmin_results = connection.execute_query(sysadmin_check_sql, usernames)
            sysadmin_dict = {row[0]: bool(row[1]) for row in sysadmin_results}
            
            # 构建动态SQL获取所有数据库的principals
            principals_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                principals_parts.append(f"""
                    SELECT '{db}' AS db_name, 
                           name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name, 
                           principal_id, 
                           sid 
                    FROM {quoted_db}.sys.database_principals 
                    WHERE type IN ('S', 'U', 'G') AND name != 'dbo'
                """)
            
            principals_sql = " UNION ALL ".join(principals_parts)
            all_principals = connection.execute_query(principals_sql)
            
            # 构建用户映射 {db: {user_name: (principal_id, sid)}}
            db_principals = {}
            for row in all_principals:
                db, user_name, pid, sid = row
                db_principals.setdefault(db, {})[user_name] = (pid, sid)
            
            # 构建动态SQL获取所有数据库的角色
            roles_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                roles_parts.append(f"""
                    SELECT '{db}' AS db_name, 
                           r.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name, 
                           m.member_principal_id 
                    FROM {quoted_db}.sys.database_role_members m
                    JOIN {quoted_db}.sys.database_principals r ON m.role_principal_id = r.principal_id
                """)
            
            roles_sql = " UNION ALL ".join(roles_parts)
            
            all_roles = connection.execute_query(roles_sql)
            
            # 构建动态SQL获取所有数据库的权限
            perms_parts = []
            for db in database_list:
                quoted_db = self._quote_identifier(db)
                perms_parts.append(f"""
                    SELECT '{db}' AS db_name, 
                           permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name, 
                           grantee_principal_id 
                    FROM {quoted_db}.sys.database_permissions WHERE state = 'G'
                """)
            
            perms_sql = " UNION ALL ".join(perms_parts)
            
            all_perms = connection.execute_query(perms_sql)
            
            # 在Python中聚合数据
            result = {}
            for username in usernames:
                result[username] = {
                    "roles": {},
                    "permissions": {}
                }
            
            # 处理角色
            for row in all_roles:
                db_name, role_name, member_principal_id = row
                
                # 查找对应的用户名
                user_name = None
                for u_name, (pid, sid) in db_principals.get(db_name, {}).items():
                    if pid == member_principal_id:
                        user_name = u_name
                        break
                
                # 如果找到用户名，添加到结果中
                if user_name in usernames:
                    if db_name not in result[user_name]["roles"]:
                        result[user_name]["roles"][db_name] = []
                    result[user_name]["roles"][db_name].append(role_name)
                
                # 通过SID匹配
                for username, sid in username_to_sid.items():
                    if sid and any(sid == db_sid for _, (_, db_sid) in db_principals.get(db_name, {}).items() if pid == member_principal_id):
                        if db_name not in result[username]["roles"]:
                            result[username]["roles"][db_name] = []
                        if role_name not in result[username]["roles"][db_name]:
                            result[username]["roles"][db_name].append(role_name)
            
            # 处理权限
            for row in all_perms:
                db_name, permission_name, grantee_principal_id = row
                
                # 查找对应的用户名
                user_name = None
                for u_name, (pid, sid) in db_principals.get(db_name, {}).items():
                    if pid == grantee_principal_id:
                        user_name = u_name
                        break
                
                # 如果找到用户名，添加到结果中
                if user_name in usernames:
                    if db_name not in result[user_name]["permissions"]:
                        result[user_name]["permissions"][db_name] = []
                    result[user_name]["permissions"][db_name].append(permission_name)
                
                # 通过SID匹配
                for username, sid in username_to_sid.items():
                    if sid and any(sid == db_sid for _, (_, db_sid) in db_principals.get(db_name, {}).items() if pid == grantee_principal_id):
                        if db_name not in result[username]["permissions"]:
                            result[username]["permissions"][db_name] = []
                        if permission_name not in result[username]["permissions"][db_name]:
                            result[username]["permissions"][db_name].append(permission_name)
            
            # 对于sysadmin用户，添加db_owner角色到所有数据库
            for username, is_sysadmin in sysadmin_dict.items():
                if is_sysadmin:
                    for db_name in database_list:
                        if db_name not in result[username]["roles"]:
                            result[username]["roles"][db_name] = []
                        if 'db_owner' not in result[username]["roles"][db_name]:
                            result[username]["roles"][db_name].append('db_owner')
            
            # 排序结果
            for username in result:
                for db_name in result[username]["roles"]:
                    result[username]["roles"][db_name].sort()
                for db_name in result[username]["permissions"]:
                    result[username]["permissions"][db_name].sort()
            
            elapsed_time = time.time() - start_time
            self.sync_logger.info(
                f"批量获取所有用户数据库权限完成",
                module="sqlserver_sync_adapter",
                user_count=len(usernames),
                database_count=len(database_list),
                elapsed_time=f"{elapsed_time:.2f}s"
            )
            
            return result
            
        except Exception as e:
            self.sync_logger.error(
                f"批量获取所有用户数据库权限失败",
                module="sqlserver_sync_adapter",
                error=str(e),
                error_type=type(e).__name__
            )
            return {}
