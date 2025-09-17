"""
泰摸鱼吧 - PostgreSQL数据库同步适配器
处理PostgreSQL特定的账户同步逻辑
"""

from typing import Any, Dict, List

from app.models import Instance
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.services.database_filter_manager import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.time_utils import time_utils

from .base_sync_adapter import BaseSyncAdapter


class PostgreSQLSyncAdapter(BaseSyncAdapter):
    """PostgreSQL数据库同步适配器"""

    def __init__(self):
        super().__init__()
        self.filter_manager = DatabaseFilterManager()

    def _safe_format_timestamp(self, timestamp) -> str | None:
        """安全地格式化时间戳，处理infinity值"""
        if timestamp is None:
            return None
        try:
            # 检查是否是infinity值
            if str(timestamp).lower() in ['infinity', '-infinity']:
                return None
            return timestamp.isoformat()
        except Exception:
            return None

    def get_database_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:
        """
        获取PostgreSQL数据库中的所有账户信息
        """
        try:
            # 构建安全的查询条件
            filter_conditions = self._build_filter_conditions()
            where_clause, params = filter_conditions

            # 查询角色基本信息
            roles_sql = f"""
                SELECT
                    rolname as username,
                    rolsuper as is_superuser,
                    rolcreaterole as can_create_role,
                    rolcreatedb as can_create_db,
                    rolreplication as can_replicate,
                    rolbypassrls as can_bypass_rls,
                    rolcanlogin as can_login,
                    rolinherit as can_inherit,
                    CASE 
                        WHEN rolvaliduntil = 'infinity'::timestamp THEN NULL
                        WHEN rolvaliduntil = '-infinity'::timestamp THEN NULL
                        ELSE rolvaliduntil
                    END as valid_until
                FROM pg_roles
                WHERE {where_clause}
                ORDER BY rolname
            """

            roles = connection.execute_query(roles_sql, params)
            
            accounts = []
            for role_row in roles:
                (username, is_superuser, can_create_role, can_create_db, 
                 can_replicate, can_bypass_rls, can_login, can_inherit, valid_until) = role_row
                
                # 获取角色详细权限
                permissions = self._get_role_permissions(connection, username, is_superuser)
                
                account_data = {
                    "username": username,
                    "is_superuser": is_superuser,
                    "can_create_role": can_create_role,
                    "can_create_db": can_create_db,
                    "can_replicate": can_replicate,
                    "can_bypass_rls": can_bypass_rls,
                    "can_login": can_login,
                    "can_inherit": can_inherit,
                    "valid_until": self._safe_format_timestamp(valid_until),
                    "permissions": permissions
                }
                
                accounts.append(account_data)

            self.sync_logger.info(
                f"获取到{len(accounts)}个PostgreSQL角色",
                module="postgresql_sync_adapter",
                instance_name=instance.name,
                account_count=len(accounts)
            )

            return accounts

        except Exception as e:
            self.sync_logger.error(
                "获取PostgreSQL角色失败",
                module="postgresql_sync_adapter",
                instance_name=instance.name,
                error=str(e)
            )
            return []

    def _build_filter_conditions(self) -> tuple[str, list]:
        """构建过滤条件"""
        filter_rules = self.filter_manager.get_filter_rules("postgresql")
        
        # 使用数据库特定的SafeQueryBuilder
        builder = SafeQueryBuilder(db_type="postgresql")
        
        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])
        
        # 使用统一的数据库特定条件构建方法（自动处理PostgreSQL特殊逻辑）
        builder.add_database_specific_condition("rolname", exclude_users, exclude_patterns)
        
        return builder.build_where_clause()

    def _get_role_permissions(self, connection: Any, username: str, is_superuser: bool) -> Dict[str, Any]:
        """
        获取PostgreSQL角色的详细权限信息
        """
        try:
            permissions = {
                "predefined_roles": [],
                "role_attributes": {},
                "database_privileges": {},
                "tablespace_privileges": {},
                "system_privileges": [],
                "type_specific": {}
            }

            # 如果是超级用户，设置超级用户属性，但仍需查询预定义角色
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

            # 获取角色属性（使用独立事务）
            try:
                role_attrs = self._get_role_attributes(connection, username)
                permissions["role_attributes"] = role_attrs
            except Exception as e:
                self.sync_logger.warning(f"获取角色属性失败: {username}", error=str(e))
                permissions["role_attributes"] = {}

            # 获取预定义角色成员关系（使用独立事务）
            try:
                predefined_roles = self._get_predefined_roles(connection, username)
                permissions["predefined_roles"] = predefined_roles
            except Exception as e:
                self.sync_logger.warning(f"获取预定义角色失败: {username}", error=str(e))
                permissions["predefined_roles"] = []

            # 获取数据库权限（使用独立事务）
            try:
                database_privileges = self._get_database_privileges(connection, username)
                permissions["database_privileges"] = database_privileges
            except Exception as e:
                self.sync_logger.warning(f"获取数据库权限失败: {username}", error=str(e))
                permissions["database_privileges"] = {}

            # 获取表空间权限（使用独立事务）
            try:
                tablespace_privileges = self._get_tablespace_privileges(connection, username)
                permissions["tablespace_privileges"] = tablespace_privileges
            except Exception as e:
                self.sync_logger.warning(f"获取表空间权限失败: {username}", error=str(e))
                permissions["tablespace_privileges"] = {}

            # 获取系统权限（使用独立事务）
            try:
                system_privileges = self._get_system_privileges(connection, username)
                permissions["system_privileges"] = system_privileges
            except Exception as e:
                self.sync_logger.warning(f"获取系统权限失败: {username}", error=str(e))
                permissions["system_privileges"] = []

            # 获取连接限制等特定信息（使用独立事务）
            try:
                type_specific = self._get_type_specific_info(connection, username)
                permissions["type_specific"] = type_specific
            except Exception as e:
                self.sync_logger.warning(f"获取特定信息失败: {username}", error=str(e))
                permissions["type_specific"] = {}

            return permissions

        except Exception as e:
            self.sync_logger.error(
                f"获取PostgreSQL角色权限失败: {username}",
                module="postgresql_sync_adapter",
                error=str(e)
            )
            return {
                "predefined_roles": [],
                "role_attributes": {},
                "database_privileges": {},
                "tablespace_privileges": {},
                "system_privileges": [],
                "type_specific": {}
            }

    def _get_role_attributes(self, connection: Any, username: str) -> Dict[str, Any]:
        """获取角色属性"""
        try:
            sql = """
                SELECT
                    rolcreaterole,
                    rolcreatedb,
                    rolcanlogin,
                    rolinherit,
                    rolreplication,
                    rolbypassrls,
                    rolconnlimit
                FROM pg_roles
                WHERE rolname = %s
            """
            result = connection.execute_query(sql, (username,))
            if result:
                attrs = result[0]
                return {
                    "can_create_role": attrs[0],
                    "can_create_db": attrs[1],
                    "can_login": attrs[2],
                    "can_inherit": attrs[3],
                    "can_replicate": attrs[4],
                    "can_bypass_rls": attrs[5],
                    "connection_limit": attrs[6]
                }
            return {}
        except Exception as e:
            self.sync_logger.warning(f"获取角色属性失败: {username}", error=str(e))
            return {}

    def _get_predefined_roles(self, connection: Any, username: str) -> List[str]:
        """获取预定义角色"""
        try:
            sql = """
                SELECT r.rolname
                FROM pg_auth_members m
                JOIN pg_roles r ON m.roleid = r.oid
                WHERE m.member = (SELECT oid FROM pg_roles WHERE rolname = %s)
                ORDER BY r.rolname
            """
            result = connection.execute_query(sql, (username,))
            return [row[0] for row in result] if result else []
        except Exception as e:
            self.sync_logger.warning(f"获取预定义角色失败: {username}", error=str(e))
            return []

    def _get_database_privileges(self, connection: Any, username: str) -> Dict[str, List[str]]:
        """获取数据库权限"""
        try:
            sql = """
                SELECT
                    table_catalog,
                    privilege_type
                FROM information_schema.table_privileges
                WHERE grantee = %s
                ORDER BY table_catalog, privilege_type
            """
            result = connection.execute_query(sql, (username,))
            
            db_privileges = {}
            if result:
                for row in result:
                    db_name, privilege = row
                    if db_name not in db_privileges:
                        db_privileges[db_name] = []
                    if privilege not in db_privileges[db_name]:
                        db_privileges[db_name].append(privilege)
            
            return db_privileges
        except Exception as e:
            self.sync_logger.warning(f"获取数据库权限失败: {username}", error=str(e))
            return {}

    def _get_tablespace_privileges(self, connection: Any, username: str) -> Dict[str, List[str]]:
        """获取表空间权限"""
        try:
            sql = """
                SELECT
                    spcname,
                    'CREATE' as privilege_type
                FROM pg_tablespace ts
                WHERE has_tablespace_privilege(%s, ts.oid, 'CREATE')
                ORDER BY spcname
            """
            result = connection.execute_query(sql, (username,))
            
            ts_privileges = {}
            if result:
                for row in result:
                    ts_name, privilege = row
                    if ts_name not in ts_privileges:
                        ts_privileges[ts_name] = []
                    ts_privileges[ts_name].append(privilege)
            
            return ts_privileges
        except Exception as e:
            self.sync_logger.warning(f"获取表空间权限失败: {username}", error=str(e))
            return {}

    def _get_system_privileges(self, connection: Any, username: str) -> List[str]:
        """获取系统权限"""
        try:
            sql = """
                SELECT DISTINCT privilege_type
                FROM information_schema.role_usage_grants
                WHERE grantee = %s
                ORDER BY privilege_type
            """
            result = connection.execute_query(sql, (username,))
            return [row[0] for row in result] if result else []
        except Exception as e:
            self.sync_logger.warning(f"获取系统权限失败: {username}", error=str(e))
            return []

    def _get_type_specific_info(self, connection: Any, username: str) -> Dict[str, Any]:
        """获取PostgreSQL特定信息"""
        try:
            # 使用pg_roles而不是pg_authid，因为pg_roles对所有用户可见
            sql = """
                SELECT
                    oid,
                    rolpassword IS NOT NULL as has_password,
                    CASE 
                        WHEN rolvaliduntil = 'infinity'::timestamp THEN NULL
                        WHEN rolvaliduntil = '-infinity'::timestamp THEN NULL
                        ELSE rolvaliduntil
                    END as valid_until
                FROM pg_roles
                WHERE rolname = %s
            """
            result = connection.execute_query(sql, (username,))
            
            if result:
                oid, has_password, valid_until = result[0]
                return {
                    "role_oid": oid,
                    "has_password": has_password,
                    "valid_until": self._safe_format_timestamp(valid_until),
                    "is_locked": False  # PostgreSQL通过can_login控制
                }
            return {}
        except Exception as e:
            self.sync_logger.warning(f"获取特定信息失败: {username}", error=str(e))
            return {}

    def extract_permissions(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """从账户数据中提取权限信息"""
        return account_data.get("permissions", {})

    def format_account_data(self, raw_account: Dict[str, Any]) -> Dict[str, Any]:
        """格式化账户数据为统一格式"""
        return {
            "username": raw_account["username"],
            "is_superuser": raw_account["is_superuser"],
            "permissions": raw_account["permissions"]
        }

    def _detect_changes(self, existing_account: CurrentAccountSyncData, 
                       new_permissions: Dict[str, Any], is_superuser: bool) -> Dict[str, Any]:
        """检测PostgreSQL账户变更"""
        changes = {}

        # 检测超级用户状态变更
        if existing_account.is_superuser != is_superuser:
            changes["is_superuser"] = {
                "old": existing_account.is_superuser,
                "new": is_superuser
            }

        # 检测预定义角色变更
        old_roles = set(existing_account.predefined_roles or [])
        new_roles = set(new_permissions.get("predefined_roles", []))
        if old_roles != new_roles:
            changes["predefined_roles"] = {
                "added": list(new_roles - old_roles),
                "removed": list(old_roles - new_roles)
            }

        # 检测角色属性变更
        old_attrs = existing_account.role_attributes or {}
        new_attrs = new_permissions.get("role_attributes", {})
        if old_attrs != new_attrs:
            changes["role_attributes"] = {
                "added": {k: v for k, v in new_attrs.items() 
                         if k not in old_attrs or old_attrs[k] != v},
                "removed": {k: v for k, v in old_attrs.items() 
                           if k not in new_attrs or new_attrs[k] != v}
            }

        # 检测数据库权限变更
        old_db_perms = existing_account.database_privileges_pg or {}
        new_db_perms = new_permissions.get("database_privileges", {})
        if old_db_perms != new_db_perms:
            changes["database_privileges"] = {
                "added": {
                    k: v for k, v in new_db_perms.items() 
                    if k not in old_db_perms or set(old_db_perms.get(k, [])) != set(v)
                },
                "removed": {
                    k: v for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(new_db_perms.get(k, [])) != set(v)
                }
            }

        # 检测表空间权限变更
        old_ts_perms = existing_account.tablespace_privileges or {}
        new_ts_perms = new_permissions.get("tablespace_privileges", {})
        if old_ts_perms != new_ts_perms:
            changes["tablespace_privileges"] = {
                "added": {
                    k: v for k, v in new_ts_perms.items()
                    if k not in old_ts_perms or set(old_ts_perms.get(k, [])) != set(v)
                },
                "removed": {
                    k: v for k, v in old_ts_perms.items()
                    if k not in new_ts_perms or set(new_ts_perms.get(k, [])) != set(v)
                }
            }

        # 检测系统权限变更
        old_sys_perms = set(existing_account.system_privileges or [])
        new_sys_perms = set(new_permissions.get("system_privileges", []))
        if old_sys_perms != new_sys_perms:
            changes["system_privileges"] = {
                "added": list(new_sys_perms - old_sys_perms),
                "removed": list(old_sys_perms - new_sys_perms)
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
                                   permissions_data: Dict[str, Any], is_superuser: bool) -> None:
        """更新PostgreSQL账户权限信息"""
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

    def _create_new_account(self, instance_id: int, db_type: str, username: str,
                           permissions_data: Dict[str, Any], is_superuser: bool,
                           session_id: str) -> CurrentAccountSyncData:
        """创建新的PostgreSQL账户记录"""
        return CurrentAccountSyncData(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            predefined_roles=permissions_data.get("predefined_roles", []),
            role_attributes=permissions_data.get("role_attributes", {}),
            database_privileges_pg=permissions_data.get("database_privileges", {}),
            tablespace_privileges=permissions_data.get("tablespace_privileges", {}),
            system_privileges=permissions_data.get("system_privileges", []),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            last_change_type="add",
            session_id=session_id
        )

    def _generate_change_description(self, db_type: str, changes: Dict[str, Any]) -> List[str]:
        """生成PostgreSQL账户变更描述"""
        descriptions = []
        
        if "is_superuser" in changes:
            old_value = changes["is_superuser"]["old"]
            new_value = changes["is_superuser"]["new"]
            if new_value:
                descriptions.append("提升为超级用户")
            else:
                descriptions.append("取消超级用户权限")
        
        if "predefined_roles" in changes:
            added = changes["predefined_roles"]["added"]
            removed = changes["predefined_roles"]["removed"]
            if added:
                descriptions.append(f"新增预定义角色: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除预定义角色: {', '.join(removed)}")
        
        if "role_attributes" in changes:
            added = changes["role_attributes"]["added"]
            removed = changes["role_attributes"]["removed"]
            if added:
                descriptions.append(f"新增角色属性: {', '.join(added.keys())}")
            if removed:
                descriptions.append(f"移除角色属性: {', '.join(removed.keys())}")
        
        if "database_privileges" in changes:
            added = changes["database_privileges"]["added"]
            removed = changes["database_privileges"]["removed"]
            if added:
                for db_name, privileges in added.items():
                    descriptions.append(f"数据库 {db_name} 新增权限: {', '.join(privileges)}")
            if removed:
                for db_name, privileges in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除权限: {', '.join(privileges)}")
        
        if "tablespace_privileges" in changes:
            added = changes["tablespace_privileges"]["added"]
            removed = changes["tablespace_privileges"]["removed"]
            if added:
                descriptions.append(f"新增表空间权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除表空间权限: {', '.join(removed)}")
        
        if "system_privileges" in changes:
            added = changes["system_privileges"]["added"]
            removed = changes["system_privileges"]["removed"]
            if added:
                descriptions.append(f"新增系统权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除系统权限: {', '.join(removed)}")
        
        if "type_specific" in changes:
            added = changes["type_specific"]["added"]
            removed = changes["type_specific"]["removed"]
            if added:
                descriptions.append(f"更新类型特定信息: {', '.join(added.keys())}")
            if removed:
                descriptions.append(f"移除类型特定信息: {', '.join(removed.keys())}")
        
        return descriptions
