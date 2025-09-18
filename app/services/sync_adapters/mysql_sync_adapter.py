"""
鲸落 - MySQL数据库同步适配器
处理MySQL特定的账户同步逻辑
"""

from typing import Any

from app.models import Instance
from app.models.current_account_sync_data import CurrentAccountSyncData
from app.services.database_filter_manager import DatabaseFilterManager
from app.utils.safe_query_builder import SafeQueryBuilder
from app.utils.time_utils import time_utils

from .base_sync_adapter import BaseSyncAdapter


class MySQLSyncAdapter(BaseSyncAdapter):
    """MySQL数据库同步适配器"""

    def __init__(self) -> None:
        super().__init__()
        self.filter_manager = DatabaseFilterManager()

    def get_database_accounts(self, instance: Instance, connection: Any) -> list[dict[str, Any]]:  # noqa: ANN401
        """
        获取MySQL数据库中的所有账户信息
        """
        try:
            # 构建安全的查询条件
            filter_conditions = self._build_filter_conditions()
            where_clause, params = filter_conditions

            # 查询用户基本信息
            user_sql = f"""
                SELECT
                    User as username,
                    Host as host,
                    Super_priv as is_superuser
                FROM mysql.user
                WHERE User != '' AND {where_clause}
                ORDER BY User, Host
            """

            users = connection.execute_query(user_sql, params)

            accounts = []
            for user_row in users:
                username, host, is_superuser = user_row

                # 为MySQL创建包含主机名的唯一用户名
                unique_username = f"{username}@{host}"

                # 获取用户权限（包含所有type_specific信息）
                permissions = self._get_user_permissions(connection, username, host)

                # 直接从数据库查询is_locked状态
                is_locked_sql = "SELECT account_locked FROM mysql.user WHERE User = %s AND Host = %s"
                is_locked_result = connection.execute_query(is_locked_sql, (username, host))
                is_locked = is_locked_result[0][0] == "Y" if is_locked_result else False

                # 将is_active信息添加到type_specific中
                permissions["type_specific"]["is_active"] = not is_locked

                account_data = {
                    "username": unique_username,
                    "original_username": username,
                    "host": host,
                    "is_superuser": is_superuser == "Y",
                    "permissions": permissions,
                }

                accounts.append(account_data)

            self.sync_logger.info(
                "获取到%d个MySQL账户",
                len(accounts),
                module="mysql_sync_adapter",
                instance_name=instance.name,
                account_count=len(accounts),
            )

            return accounts

        except Exception as e:
            self.sync_logger.error(
                "获取MySQL账户失败", module="mysql_sync_adapter", instance_name=instance.name, error=str(e)
            )
            return []

    def _build_filter_conditions(self) -> tuple[str, list]:
        """构建过滤条件"""
        filter_rules = self.filter_manager.get_filter_rules("mysql")

        # 使用数据库特定的SafeQueryBuilder
        builder = SafeQueryBuilder(db_type="mysql")

        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])

        # 使用统一的数据库特定条件构建方法
        builder.add_database_specific_condition("User", exclude_users, exclude_patterns)

        return builder.build_where_clause()

    def _get_user_permissions(self, connection: Any, username: str, host: str) -> dict[str, Any]:  # noqa: ANN401
        """
        获取MySQL用户的详细权限信息
        """
        try:
            # 获取用户权限语句
            grants = connection.execute_query("SHOW GRANTS FOR %s@%s", (username, host))
            grant_statements = [row[0] for row in grants]

            # 解析权限
            global_privileges = []
            database_privileges = {}

            for grant_statement in grant_statements:
                self._parse_grant_statement(grant_statement, global_privileges, database_privileges)

            # 获取用户的额外属性信息
            user_attrs_sql = """
                SELECT
                    Grant_priv as can_grant,
                    account_locked as is_locked,
                    plugin as plugin,
                    password_last_changed as password_last_changed
                FROM mysql.user
                WHERE User = %s AND Host = %s
            """
            user_attrs = connection.execute_query(user_attrs_sql, (username, host))

            # 构建type_specific信息
            type_specific = {"host": host, "original_username": username, "grant_statements": grant_statements}

            # 添加用户属性信息
            if user_attrs:
                attrs = user_attrs[0]
                type_specific.update(
                    {
                        "can_grant": attrs[0] == "Y",
                        "is_locked": attrs[1] == "Y",  # 添加is_locked字段
                        "plugin": attrs[2],
                        "password_last_changed": attrs[3].isoformat() if attrs[3] else None,
                    }
                )

            return {
                "global_privileges": global_privileges,
                "database_privileges": database_privileges,
                "type_specific": type_specific,
            }

        except Exception as e:
            self.sync_logger.error(
                "获取MySQL用户权限失败: %s@%s", username, host, module="mysql_sync_adapter", error=str(e)
            )
            return {
                "global_privileges": [],
                "database_privileges": {},
                "type_specific": {"host": host, "original_username": username},
            }

    def _parse_grant_statement(
        self, grant_statement: str, global_privileges: list[str], database_privileges: dict[str, list[str]]
    ) -> None:
        """
        解析GRANT语句
        """
        try:
            grant_upper = grant_statement.upper()

            if "GRANT ALL PRIVILEGES" in grant_upper:
                if "ON *.*" in grant_upper:
                    global_privileges.append("ALL PRIVILEGES")
                elif "ON `" in grant_upper and "`.*" in grant_upper:
                    # 数据库级别的ALL PRIVILEGES
                    db_name = self._extract_database_name(grant_statement)
                    if db_name:
                        if db_name not in database_privileges:
                            database_privileges[db_name] = []
                        database_privileges[db_name].append("ALL PRIVILEGES")
            elif "ON *.*" in grant_upper:
                # 全局权限
                privileges = self._extract_privileges_from_grant(grant_statement)
                global_privileges.extend(privileges)
            elif "ON `" in grant_upper and "`.*" in grant_upper:
                # 数据库权限
                db_name = self._extract_database_name(grant_statement)
                privileges = self._extract_privileges_from_grant(grant_statement)
                if db_name and privileges:
                    if db_name not in database_privileges:
                        database_privileges[db_name] = []
                    database_privileges[db_name].extend(privileges)

        except Exception as e:
            self.sync_logger.warning(
                "解析GRANT语句失败: %s", grant_statement, module="mysql_sync_adapter", error=str(e)
            )

    def _extract_database_name(self, grant_statement: str) -> str:
        """从GRANT语句中提取数据库名"""
        try:
            if "ON `" in grant_statement and "`.*" in grant_statement:
                start = grant_statement.find("ON `") + 4
                end = grant_statement.find("`.*", start)
                return grant_statement[start:end]
        except Exception as e:
            self.sync_logger.warning(
                "提取数据库名失败",
                module="mysql_sync_adapter",
                grant_statement=grant_statement,
                error=str(e)
            )
        return ""

    def _extract_privileges_from_grant(self, grant_statement: str) -> list[str]:
        """从GRANT语句中提取权限列表"""
        try:
            # 提取GRANT和ON之间的权限部分
            grant_part = grant_statement.split("ON")[0].replace("GRANT ", "").strip()

            # 分割权限并清理
            privileges = []
            for priv in grant_part.split(","):
                priv = priv.strip()
                if priv and priv not in privileges:
                    privileges.append(priv)

            return privileges
        except Exception:
            return []

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
        """检测MySQL账户变更"""
        changes = {}

        # 检测超级用户状态变更
        if existing_account.is_superuser != is_superuser:
            changes["is_superuser"] = {"old": existing_account.is_superuser, "new": is_superuser}

        # 检测is_active状态变更（从type_specific中获取）
        new_is_active = new_permissions.get("type_specific", {}).get("is_active", False)
        if existing_account.is_active != new_is_active:
            changes["is_active"] = {"old": existing_account.is_active, "new": new_is_active}

        # 检测全局权限变更
        old_global = set(existing_account.global_privileges or [])
        new_global = set(new_permissions.get("global_privileges", []))
        if old_global != new_global:
            changes["global_privileges"] = {
                "added": list(new_global - old_global),
                "removed": list(old_global - new_global),
            }

        # 检测数据库权限变更
        old_db_perms = existing_account.database_privileges or {}
        new_db_perms = new_permissions.get("database_privileges", {})
        if old_db_perms != new_db_perms:
            changes["database_privileges"] = {
                "added": {
                    k: v
                    for k, v in new_db_perms.items()
                    if k not in old_db_perms or set(old_db_perms.get(k, [])) != set(v)
                },
                "removed": {
                    k: v
                    for k, v in old_db_perms.items()
                    if k not in new_db_perms or set(new_db_perms.get(k, [])) != set(v)
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
        """更新MySQL账户权限信息"""
        account.global_privileges = permissions_data.get("global_privileges", [])
        account.database_privileges = permissions_data.get("database_privileges", {})
        account.type_specific = permissions_data.get("type_specific", {})
        account.is_superuser = is_superuser
        # 从type_specific中获取is_active状态
        account.is_active = permissions_data.get("type_specific", {}).get("is_active", False)
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
        """创建新的MySQL账户记录"""
        return CurrentAccountSyncData(
            instance_id=instance_id,
            db_type=db_type,
            username=username,
            global_privileges=permissions_data.get("global_privileges", []),
            database_privileges=permissions_data.get("database_privileges", {}),
            type_specific=permissions_data.get("type_specific", {}),
            is_superuser=is_superuser,
            # 从type_specific中获取is_active状态
            is_active=permissions_data.get("type_specific", {}).get("is_active", False),
            last_change_type="add",
            session_id=session_id,
        )

    def _generate_change_description(self, db_type: str, changes: dict[str, Any]) -> list[str]:
        """生成MySQL账户变更描述"""
        descriptions = []

        if "is_superuser" in changes:
            new_value = changes["is_superuser"]["new"]
            if new_value:
                descriptions.append("提升为超级用户")
            else:
                descriptions.append("取消超级用户权限")

        if "global_privileges" in changes:
            added = changes["global_privileges"]["added"]
            removed = changes["global_privileges"]["removed"]
            if added:
                descriptions.append(f"新增全局权限: {', '.join(added)}")
            if removed:
                descriptions.append(f"移除全局权限: {', '.join(removed)}")

        if "database_privileges" in changes:
            added = changes["database_privileges"]["added"]
            removed = changes["database_privileges"]["removed"]
            if added:
                for db_name, privileges in added.items():
                    descriptions.append(f"数据库 {db_name} 新增权限: {', '.join(privileges)}")
            if removed:
                for db_name, privileges in removed.items():
                    descriptions.append(f"数据库 {db_name} 移除权限: {', '.join(privileges)}")

        if "type_specific" in changes:
            added = changes["type_specific"]["added"]
            removed = changes["type_specific"]["removed"]
            if added:
                descriptions.append(f"更新类型特定信息: {', '.join(added.keys())}")
            if removed:
                descriptions.append(f"移除类型特定信息: {', '.join(removed.keys())}")

        return descriptions
