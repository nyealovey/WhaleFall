"""
泰摸鱼吧 - Oracle数据库同步适配器
处理Oracle特定的账户同步逻辑
"""

import contextlib
from typing import Any

from app.models import Instance
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.services.database_filter_manager import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.time_utils import time_utils

from .base_sync_adapter import BaseSyncAdapter


class OracleSyncAdapter(BaseSyncAdapter):
    """Oracle数据库同步适配器"""

    def __init__(self) -> None:
        super().__init__()
        self.filter_manager = DatabaseFilterManager()

    def get_database_accounts(self, instance: Instance, connection: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """
        获取Oracle数据库中的所有账户信息（优化版本）
        使用批量查询减少N+1查询问题，从O(N)降到O(1)
        """
        try:
            # 构建安全的查询条件
            filter_conditions = self._build_filter_conditions()
            where_clause, params = filter_conditions

            # 1. 一次性查询所有用户基本信息（包含user_id用于后续查询）
            users_sql = f"""
                SELECT
                    username,
                    user_id,
                    account_status,
                    created,
                    expiry_date,
                    default_tablespace,
                    temporary_tablespace,
                    profile
                FROM dba_users
                WHERE {where_clause}
                ORDER BY username
            """

            users = connection.execute_query(users_sql, params)
            
            # 空用户检查，早返回
            if not users:
                self.sync_logger.info(
                    "未找到符合条件的Oracle用户",
                    module="oracle_sync_adapter",
                    instance_name=instance.name,
                )
                return []

            # 提取所有用户名列表用于批量查询
            usernames = [user_row[0] for user_row in users]
            username_placeholders = ",".join([f":username_{i}" for i in range(len(usernames))])
            username_params = {f"username_{i}": username for i, username in enumerate(usernames)}

            # 2. 批量查询所有用户的角色权限
            roles_data = self._batch_get_user_roles(connection, username_placeholders, username_params)
            
            # 3. 批量查询所有用户的系统权限
            system_privs_data = self._batch_get_system_privileges(connection, username_placeholders, username_params)
            
            # 4. 批量查询所有用户的表空间权限
            tablespace_data = self._batch_get_tablespace_privileges(connection, username_placeholders, username_params, system_privs_data)
            
            # 5. 批量查询所有用户的对象权限（可选）
            object_perms_data = self._batch_get_object_privileges(connection, username_placeholders, username_params)

            # 6. 在Python侧聚合所有权限数据
            accounts = []
            for user_row in users:
                (username, user_id, account_status, created, expiry_date, default_tablespace, temporary_tablespace, profile) = user_row
                
                # 从批量查询结果中获取该用户的权限
                permissions = {
                    "roles": roles_data.get(username, []),
                    "system_privileges": system_privs_data.get(username, []),
                    "tablespace_privileges": tablespace_data.get(username, {}),
                    "type_specific": {
                        "user_id": user_id,
                        "account_status": account_status,
                        "default_tablespace": default_tablespace,
                        "temporary_tablespace": temporary_tablespace,
                        "profile": profile,
                        "created": created.isoformat() if created else None,
                        "expiry_date": expiry_date.isoformat() if expiry_date else None,
                        "is_active": account_status == "OPEN",  # 直接从account_status推导
                    }
                }
                
                # 添加对象权限（如果可用）
                if username in object_perms_data:
                    permissions["object_privileges"] = object_perms_data[username]

                # 判断是否为超级用户
                is_superuser = username.upper() in ["SYS", "SYSTEM"] or "DBA" in permissions["roles"]

                account_data = {
                    "username": username,
                    "is_superuser": is_superuser,
                    "account_status": account_status,
                    "created": created.isoformat() if created else None,
                    "expiry_date": expiry_date.isoformat() if expiry_date else None,
                    "default_tablespace": default_tablespace,
                    "temporary_tablespace": temporary_tablespace,
                    "profile": profile,
                    "permissions": permissions,
                }

                accounts.append(account_data)

            self.sync_logger.info(
                "获取到%d个Oracle用户（批量查询优化）",
                len(accounts),
                module="oracle_sync_adapter",
                instance_name=instance.name,
                account_count=len(accounts),
            )

            return accounts

        except Exception as e:
            self.sync_logger.error(
                "获取Oracle用户失败", module="oracle_sync_adapter", instance_name=instance.name, error=str(e)
            )
            return []

    def _build_filter_conditions(self) -> tuple[str, dict]:
        """构建Oracle专用的过滤条件"""
        filter_rules = self.filter_manager.get_filter_rules("oracle")

        # 使用数据库特定的SafeQueryBuilder
        builder = SafeQueryBuilder(db_type="oracle")

        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])

        # 使用统一的数据库特定条件构建方法
        builder.add_database_specific_condition("username", exclude_users, exclude_patterns)

        return builder.build_where_clause()

    def _batch_get_user_roles(self, connection: Any, username_placeholders: str, username_params: dict) -> dict[str, list[str]]:  # noqa: ANN401
        """批量获取所有用户的角色权限"""
        try:
            sql = f"""
                SELECT grantee, granted_role
                FROM dba_role_privs
                WHERE grantee IN ({username_placeholders})
                ORDER BY grantee, granted_role
            """
            result = connection.execute_query(sql, username_params)
            
            # 聚合结果
            roles_data = {}
            for grantee, role in result:
                if grantee not in roles_data:
                    roles_data[grantee] = []
                roles_data[grantee].append(role)
            
            return roles_data
        except Exception as e:
            self.sync_logger.warning("批量获取用户角色失败", error=str(e))
            return {}

    def _batch_get_system_privileges(self, connection: Any, username_placeholders: str, username_params: dict) -> dict[str, list[str]]:  # noqa: ANN401
        """批量获取所有用户的系统权限"""
        try:
            sql = f"""
                SELECT grantee, privilege
                FROM dba_sys_privs
                WHERE grantee IN ({username_placeholders})
                ORDER BY grantee, privilege
            """
            result = connection.execute_query(sql, username_params)
            
            # 聚合结果
            system_privs_data = {}
            for grantee, privilege in result:
                if grantee not in system_privs_data:
                    system_privs_data[grantee] = []
                system_privs_data[grantee].append(privilege)
            
            return system_privs_data
        except Exception as e:
            self.sync_logger.warning("批量获取系统权限失败", error=str(e))
            return {}

    def _batch_get_tablespace_privileges(self, connection: Any, username_placeholders: str, username_params: dict, system_privs_data: dict) -> dict[str, dict[str, list[str]]]:  # noqa: ANN401
        """批量获取所有用户的表空间权限"""
        try:
            tablespace_data = {}
            
            # 1. 检查UNLIMITED TABLESPACE权限（从系统权限中获取）
            for username, privileges in system_privs_data.items():
                if "UNLIMITED TABLESPACE" in privileges:
                    tablespace_data[username] = {"ALL_TABLESPACES": ["UNLIMITED"]}
            
            # 2. 批量查询表空间配额
            try:
                ts_quota_sql = f"""
                    SELECT username, tablespace_name,
                           CASE
                               WHEN max_bytes = -1 THEN 'UNLIMITED'
                               ELSE 'QUOTA'
                           END as privilege
                    FROM dba_ts_quotas
                    WHERE username IN ({username_placeholders})
                    ORDER BY username, tablespace_name
                """
                ts_quota_result = connection.execute_query(ts_quota_sql, username_params)
                
                for username, ts_name, privilege in ts_quota_result:
                    if username not in tablespace_data:
                        tablespace_data[username] = {}
                    if ts_name not in tablespace_data[username]:
                        tablespace_data[username][ts_name] = []
                    if privilege not in tablespace_data[username][ts_name]:
                        tablespace_data[username][ts_name].append(privilege)
            except Exception as e:
                self.sync_logger.warning("批量获取表空间配额失败", error=str(e))
            
            return tablespace_data
        except Exception as e:
            self.sync_logger.warning("批量获取表空间权限失败", error=str(e))
            return {}

    def _batch_get_object_privileges(self, connection: Any, username_placeholders: str, username_params: dict) -> dict[str, dict[str, list[str]]]:  # noqa: ANN401
        """批量获取所有用户的对象权限（可选）"""
        try:
            # 先检查dba_tables表是否存在
            check_tables_sql = "SELECT COUNT(*) FROM dba_tables WHERE ROWNUM = 1"
            connection.execute_query(check_tables_sql)
            
            # 批量查询对象权限
            object_perms_sql = f"""
                SELECT owner, tablespace_name, 'OWNER' as privilege
                FROM dba_tables
                WHERE owner IN ({username_placeholders})
                AND tablespace_name IS NOT NULL
                
                UNION
                
                SELECT owner, tablespace_name, 'INDEX_OWNER' as privilege
                FROM dba_indexes
                WHERE owner IN ({username_placeholders})
                AND tablespace_name IS NOT NULL
                
                ORDER BY owner, tablespace_name, privilege
            """
            
            result = connection.execute_query(object_perms_sql, username_params)
            
            # 聚合结果
            object_perms_data = {}
            for owner, ts_name, privilege in result:
                if owner not in object_perms_data:
                    object_perms_data[owner] = {}
                if ts_name not in object_perms_data[owner]:
                    object_perms_data[owner][ts_name] = []
                if privilege not in object_perms_data[owner][ts_name]:
                    object_perms_data[owner][ts_name].append(privilege)
            
            return object_perms_data
        except Exception as e:
            self.sync_logger.warning("批量获取对象权限失败", error=str(e))
            return {}

    def _get_user_permissions(self, connection: Any, username: str) -> dict[str, Any]:  # noqa: ANN401
        """
        获取Oracle用户的详细权限信息
        """
        try:
            permissions = {"roles": [], "system_privileges": [], "tablespace_privileges": {}, "type_specific": {}}

            # 获取用户角色
            roles = self._get_user_roles(connection, username)
            permissions["roles"] = roles

            # 获取系统权限
            system_privileges = self._get_system_privileges(connection, username)
            permissions["system_privileges"] = system_privileges

            # 获取表空间权限
            tablespace_privileges = self._get_tablespace_privileges(connection, username)
            permissions["tablespace_privileges"] = tablespace_privileges

            # 获取特定信息
            type_specific = self._get_type_specific_info(connection, username)
            permissions["type_specific"] = type_specific

            return permissions

        except Exception as e:
            self.sync_logger.error("获取Oracle用户权限失败: %s", username, module="oracle_sync_adapter", error=str(e))
            return {"roles": [], "system_privileges": [], "tablespace_privileges": {}, "type_specific": {}}

    def _get_user_roles(self, connection: Any, username: str) -> list[str]:  # noqa: ANN401
        """获取用户角色"""
        try:
            sql = """
                SELECT granted_role
                FROM dba_role_privs
                WHERE grantee = :username
                ORDER BY granted_role
            """
            result = connection.execute_query(sql, {"username": username})
            return [row[0] for row in result] if result else []
        except Exception as e:
            self.sync_logger.warning("获取用户角色失败: %s", username, error=str(e))
            return []

    def _get_system_privileges(self, connection: Any, username: str) -> list[str]:  # noqa: ANN401
        """获取系统权限"""
        try:
            sql = """
                SELECT privilege
                FROM dba_sys_privs
                WHERE grantee = :username
                ORDER BY privilege
            """
            result = connection.execute_query(sql, {"username": username})
            return [row[0] for row in result] if result else []
        except Exception as e:
            self.sync_logger.warning("获取系统权限失败: %s", username, error=str(e))
            return []

    def _get_tablespace_privileges(self, connection: Any, username: str) -> dict[str, list[str]]:  # noqa: ANN401
        """获取表空间权限"""
        try:
            tablespace_privileges = {}

            # 1. 检查是否有UNLIMITED TABLESPACE系统权限
            try:
                system_privs_sql = """
                    SELECT privilege
                    FROM dba_sys_privs
                    WHERE grantee = :username AND privilege = 'UNLIMITED TABLESPACE'
                """
                unlimited_result = connection.execute_query(system_privs_sql, {"username": username})

                if unlimited_result:
                    tablespace_privileges["ALL_TABLESPACES"] = ["UNLIMITED"]
            except Exception as e:
                pass

            # 2. 获取具体的表空间配额信息
            try:
                ts_quota_sql = """
                    SELECT tablespace_name,
                           CASE
                               WHEN max_bytes = -1 THEN 'UNLIMITED'
                               ELSE 'QUOTA'
                           END as privilege
                    FROM dba_ts_quotas
                    WHERE username = :username
                    ORDER BY tablespace_name
                """
                ts_quota_result = connection.execute_query(ts_quota_sql, {"username": username})

                if ts_quota_result:
                    for ts_name, privilege in ts_quota_result:
                        if ts_name not in tablespace_privileges:
                            tablespace_privileges[ts_name] = []
                        if privilege not in tablespace_privileges[ts_name]:
                            tablespace_privileges[ts_name].append(privilege)
            except Exception as e:
                # 如果dba_ts_quotas不可用，尝试使用user_ts_quotas
                with contextlib.suppress(Exception):
                    # 这里需要切换到目标用户上下文，但为了安全起见，跳过这个查询
                    pass

            # 3. 获取用户在表空间中的对象权限（可选，如果表存在）
            try:
                # 先检查dba_tables表是否存在
                check_tables_sql = """
                    SELECT COUNT(*) FROM dba_tables WHERE ROWNUM = 1
                """
                connection.execute_query(check_tables_sql)

                # 如果dba_tables存在，则查询对象权限
                user_objects_sql = """
                    SELECT DISTINCT tablespace_name, 'OWNER' as privilege
                    FROM dba_tables
                    WHERE owner = :username
                    AND tablespace_name IS NOT NULL

                    UNION

                    SELECT DISTINCT tablespace_name, 'INDEX_OWNER' as privilege
                    FROM dba_indexes
                    WHERE owner = :username
                    AND tablespace_name IS NOT NULL

                    ORDER BY tablespace_name, privilege
                """
                objects_result = connection.execute_query(user_objects_sql, {"username": username})

                if objects_result:
                    for ts_name, privilege in objects_result:
                        if ts_name not in tablespace_privileges:
                            tablespace_privileges[ts_name] = []
                        if privilege not in tablespace_privileges[ts_name]:
                            tablespace_privileges[ts_name].append(privilege)
            except Exception as e:
                pass

            return tablespace_privileges

        except Exception as e:
            self.sync_logger.warning("获取表空间权限失败: %s", username, error=str(e))
            return {}

    def _get_type_specific_info(self, connection: Any, username: str) -> dict[str, Any]:  # noqa: ANN401
        """获取Oracle特定信息"""
        try:
            # 获取用户详细信息
            sql = """
                SELECT
                    user_id,
                    account_status,
                    default_tablespace,
                    temporary_tablespace,
                    profile,
                    created,
                    expiry_date
                FROM dba_users
                WHERE username = :username
            """

            result = connection.execute_query(sql, {"username": username})

            if result:
                (user_id, account_status, default_tablespace, temporary_tablespace, profile, created, expiry_date) = (
                    result[0]
                )

                return {
                    "user_id": user_id,
                    "default_tablespace": default_tablespace,
                    "temporary_tablespace": temporary_tablespace,
                    "profile": profile,
                    "created": created.isoformat() if created else None,
                    "expiry_date": expiry_date.isoformat() if expiry_date else None,
                    # 移除is_locked和account_status，因为已有专门的is_active字段
                }
            return {}
        except Exception as e:
            self.sync_logger.warning("获取特定信息失败: %s", username, error=str(e))
            return {}

    def extract_permissions(self, account_data: dict[str, Any]) -> dict[str, Any]:
        """从账户数据中提取权限信息"""
        return account_data.get("permissions", {})

    def format_account_data(self, raw_account: dict[str, Any]) -> dict[str, Any]:
        """格式化账户数据为统一格式"""
        return {
            "username": raw_account["username"],
            "is_superuser": raw_account["is_superuser"],
            "permissions": raw_account["permissions"],
        }

    def _detect_changes(
        self, existing_account: CurrentAccountSyncData, new_permissions: dict[str, Any], *, is_superuser: bool
    ) -> dict[str, Any]:
        """检测Oracle账户变更"""
        changes = {}

        # 检测超级用户状态变更
        if existing_account.is_superuser != is_superuser:
            changes["is_superuser"] = {"old": existing_account.is_superuser, "new": is_superuser}

        # 检测is_active状态变更（从type_specific中获取）
        new_is_active = new_permissions.get("type_specific", {}).get("is_active", False)
        if existing_account.is_active != new_is_active:
            changes["is_active"] = {"old": existing_account.is_active, "new": new_is_active}

        # 检测角色变更
        old_roles = set(existing_account.oracle_roles or [])
        new_roles = set(new_permissions.get("roles", []))
        if old_roles != new_roles:
            changes["oracle_roles"] = {"added": list(new_roles - old_roles), "removed": list(old_roles - new_roles)}

        # 检测系统权限变更
        old_system_perms = set(existing_account.system_privileges or [])
        new_system_perms = set(new_permissions.get("system_privileges", []))
        if old_system_perms != new_system_perms:
            changes["system_privileges"] = {
                "added": list(new_system_perms - old_system_perms),
                "removed": list(old_system_perms - new_system_perms),
            }

        # 检测表空间权限变更
        old_tablespace_perms = existing_account.tablespace_privileges_oracle or {}
        new_tablespace_perms = new_permissions.get("tablespace_privileges", {})

        # 使用集合比较，忽略顺序
        old_ts_perms_set = {k: set(v) for k, v in old_tablespace_perms.items()}
        new_ts_perms_set = {k: set(v) for k, v in new_tablespace_perms.items()}

        if old_ts_perms_set != new_ts_perms_set:
            changes["tablespace_privileges"] = {
                "added": {
                    k: v
                    for k, v in new_tablespace_perms.items()
                    if k not in old_tablespace_perms or set(old_tablespace_perms.get(k, [])) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_tablespace_perms.items()
                    if k not in new_tablespace_perms or set(new_tablespace_perms.get(k, [])) != set(v)
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
        self, account: CurrentAccountSyncData, permissions_data: dict[str, Any], is_superuser: bool
    ) -> None:
        """更新Oracle账户权限信息"""
        account.oracle_roles = permissions_data.get("roles", [])
        account.system_privileges = permissions_data.get("system_privileges", [])
        account.tablespace_privileges_oracle = permissions_data.get("tablespace_privileges", {})
        account.type_specific = permissions_data.get("type_specific", {})
        account.is_superuser = is_superuser
        # 从type_specific中获取is_active状态
        account.is_active = permissions_data.get("type_specific", {}).get("is_active", False)
        account.is_deleted = False  # 重置删除状态
        account.deleted_time = None  # 清除删除时间
        account.last_change_type = "modify_privilege"
        account.last_change_time = time_utils.now()
        account.last_sync_time = time_utils.now()

    def _create_new_account(
        self,
        instance_id: int,
        db_type: str,
        username: str,
        permissions_data: dict[str, Any],
        *,
        is_superuser: bool,
        session_id: str,
    ) -> CurrentAccountSyncData:
        """创建新的Oracle账户记录"""
        return CurrentAccountSyncData(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            oracle_roles=permissions_data.get("roles", []),
            system_privileges=permissions_data.get("system_privileges", []),
            tablespace_privileges_oracle=permissions_data.get("tablespace_privileges", {}),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            # 从type_specific中获取is_active状态
            is_active=permissions_data.get("type_specific", {}).get("is_active", False),
            last_change_type="add",
            session_id=session_id,
        )

    def _generate_change_description(self, db_type: str, changes: dict[str, Any]) -> list[str]:
        """生成Oracle账户变更描述"""
        descriptions = []

        if "is_superuser" in changes:
            new_value = changes["is_superuser"]["new"]
            if new_value:
                descriptions.append("提升为超级用户")
            else:
                descriptions.append("取消超级用户权限")

        if "is_active" in changes:
            new_value = changes["is_active"]["new"]
            if new_value:
                descriptions.append("账户状态变更为活跃")
            else:
                descriptions.append("账户状态变更为锁定")

        if "oracle_roles" in changes:
            added = changes["oracle_roles"]["added"]
            removed = changes["oracle_roles"]["removed"]
            if added:
                descriptions.append(f"新增Oracle角色: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除Oracle角色: {', '.join(removed)}")

        if "system_privileges" in changes:
            added = changes["system_privileges"]["added"]
            removed = changes["system_privileges"]["removed"]
            if added:
                descriptions.append(f"新增系统权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除系统权限: {', '.join(removed)}")

        if "tablespace_privileges_oracle" in changes:
            added = changes["tablespace_privileges_oracle"]["added"]
            removed = changes["tablespace_privileges_oracle"]["removed"]
            if added:
                for ts_name, privileges in added.items():
                    descriptions.append(f"表空间 {ts_name} 新增权限: {', '.join(privileges)}")
            if removed:
                for ts_name, privileges in removed.items():
                    descriptions.append(f"表空间 {ts_name} 移除权限: {', '.join(privileges)}")

        if "type_specific" in changes:
            added = changes["type_specific"]["added"]
            removed = changes["type_specific"]["removed"]
            if added:
                descriptions.append(f"更新类型特定信息: {', '.join(added.keys())}")
            if removed:
                descriptions.append(f"移除类型特定信息: {', '.join(removed.keys())}")

        return descriptions
