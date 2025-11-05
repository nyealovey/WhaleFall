"""SQL Server 账户同步适配器（两阶段版）。"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Sequence

from app.constants import DatabaseType
from app.models.instance import Instance
from app.services.account_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.account_sync.account_sync_filters import DatabaseFilterManager
from app.utils.structlog_config import get_sync_logger
from app.services.cache_service import cache_manager


class SQLServerAccountAdapter(BaseAccountAdapter):
    def __init__(self) -> None:
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    def _fetch_raw_accounts(self, instance: Instance, connection: Any) -> List[Dict[str, Any]]:  # noqa: ANN401
        try:
            users = self._fetch_logins(connection)
            accounts: List[Dict[str, Any]] = []
            for user in users:
                login_name = user["name"]
                is_disabled = user.get("is_disabled", False)
                is_superuser = user.get("is_sysadmin", False)
                accounts.append(
                    {
                        "username": login_name,
                        "is_superuser": is_superuser,
                        "is_disabled": is_disabled,
                        "permissions": {
                            "type_specific": {
                                "is_disabled": is_disabled,
                            }
                        },
                    }
                )
            self.logger.info(
                "fetch_sqlserver_accounts_success",
                module="sqlserver_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_sqlserver_accounts_failed",
                module="sqlserver_account_adapter",
                instance=instance.name,
                error=str(exc),
                exc_info=True,
            )
            return []

    def _normalize_account(self, instance: Instance, account: Dict[str, Any]) -> Dict[str, Any]:
        permissions = account.get("permissions", {})
        type_specific = permissions.setdefault("type_specific", {})
        type_specific.setdefault("is_disabled", account.get("is_disabled", False))
        attributes = {
            "is_disabled": type_specific.get("is_disabled", account.get("is_disabled", False)),
        }
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.SQLSERVER,
            "is_superuser": account.get("is_superuser", False),
            "is_active": not account.get("is_disabled", False),
            "attributes": attributes,
            "permissions": {
                "server_roles": permissions.get("server_roles", []),
                "server_permissions": permissions.get("server_permissions", []),
                "database_roles": permissions.get("database_roles", {}),
                "database_permissions": permissions.get("database_permissions", {}),
                "type_specific": permissions.get("type_specific", {}),
            },
        }

    def enrich_permissions(
        self,
        instance: Instance,
        connection: Any,
        accounts: List[Dict[str, Any]],
        *,
        usernames: List[str] | None = None,
    ) -> List[Dict[str, Any]]:
        target_usernames = {account["username"] for account in accounts} if usernames is None else set(usernames)
        if not target_usernames:
            return accounts

        usernames_list = list(target_usernames)
        server_roles_map = self._get_server_roles_bulk(connection, usernames_list)
        server_permissions_map = self._get_server_permissions_bulk(connection, usernames_list)
        db_batch_permissions = self._get_all_users_database_permissions_batch_optimized(connection, usernames_list)
        db_permissions_map: Dict[str, Dict[str, Any]] = {
            login: data.get("permissions", {})
            for login, data in db_batch_permissions.items()
        }
        db_roles_map: Dict[str, Dict[str, List[str]]] = {
            login: data.get("roles", {})
            for login, data in db_batch_permissions.items()
        }
        processed = 0
        for account in accounts:
            username = account.get("username")
            if not username or username not in target_usernames:
                continue
            processed += 1
            try:
                permissions = self._get_login_permissions(
                    connection,
                    username,
                    precomputed_server_roles=server_roles_map,
                    precomputed_server_permissions=server_permissions_map,
                    precomputed_db_roles=db_roles_map,
                    precomputed_db_permissions=db_permissions_map,
                )
                type_specific = permissions.setdefault("type_specific", {})
                existing_type_specific = account.get("permissions", {}).get("type_specific", {})
                if isinstance(existing_type_specific, dict):
                    for key, value in existing_type_specific.items():
                        if value is not None:
                            type_specific.setdefault(key, value)
                attributes = account.get("attributes") or {}
                if isinstance(attributes, dict):
                    for key, value in attributes.items():
                        if value is not None:
                            type_specific.setdefault(key, value)
                type_specific.setdefault("is_disabled", account.get("is_disabled", False))
                account["permissions"] = permissions
            except Exception as exc:  # noqa: BLE001
                self.logger.error(
                    "fetch_sqlserver_permissions_failed",
                    module="sqlserver_account_adapter",
                    instance=instance.name,
                    username=username,
                    error=str(exc),
                    exc_info=True,
                )
                account.setdefault("permissions", {}).setdefault("errors", []).append(str(exc))

        self.logger.info(
            "fetch_sqlserver_permissions_completed",
            module="sqlserver_account_adapter",
            instance=instance.name,
            processed_accounts=processed,
        )
        return accounts

    # ------------------------------------------------------------------
    # 查询逻辑来源于旧实现
    # ------------------------------------------------------------------
    def _fetch_logins(self, connection: Any) -> List[Dict[str, Any]]:
        filter_rules = self.filter_manager.get_filter_rules("sqlserver")
        exclude_users = filter_rules.get("exclude_users", [])
        exclude_patterns = filter_rules.get("exclude_patterns", [])

        sql = """
            SELECT
                sp.name,
                sp.type_desc,
                sp.is_disabled,
                IS_SRVROLEMEMBER('sysadmin', sp.name) AS is_sysadmin
            FROM sys.server_principals sp
            WHERE sp.type IN ('S', 'U', 'G')
        """
        params: list[Any] = []
        if exclude_users:
            placeholders = ", ".join(["%s"] * len(exclude_users))
            sql += f" AND sp.name NOT IN ({placeholders})"
            params.extend(exclude_users)
        rows = connection.execute_query(sql, tuple(params) if params else None)

        results: List[Dict[str, Any]] = []
        for row in rows:
            name = row[0]
            if any(pattern and pattern in name for pattern in exclude_patterns):
                continue
            results.append(
                {
                    "name": name,
                    "type_desc": row[1],
                    "is_disabled": bool(row[2]),
                    "is_sysadmin": bool(row[3]),
                }
            )
        return results

    def _get_login_permissions(
        self,
        connection: Any,
        login_name: str,
        *,
        precomputed_server_roles: Dict[str, List[str]] | None = None,
        precomputed_server_permissions: Dict[str, List[str]] | None = None,
        precomputed_db_roles: Dict[str, Dict[str, List[str]]] | None = None,
        precomputed_db_permissions: Dict[str, Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        if precomputed_server_roles is not None and login_name in precomputed_server_roles:
            server_roles = self._deduplicate_preserve_order(precomputed_server_roles.get(login_name, []))
        else:
            server_roles = self._deduplicate_preserve_order(self._get_server_roles(connection, login_name))

        if precomputed_server_permissions is not None and login_name in precomputed_server_permissions:
            server_permissions = self._deduplicate_preserve_order(precomputed_server_permissions.get(login_name, []))
        else:
            server_permissions = self._deduplicate_preserve_order(self._get_server_permissions(connection, login_name))

        if precomputed_db_roles is not None and login_name in precomputed_db_roles:
            database_roles = {
                db_name: self._deduplicate_preserve_order(roles or [])
                for db_name, roles in (precomputed_db_roles.get(login_name) or {}).items()
            }
        else:
            database_roles = {
                db_name: self._deduplicate_preserve_order(roles or [])
                for db_name, roles in self._get_database_roles(connection, login_name).items()
            }

        if precomputed_db_permissions is not None and login_name in precomputed_db_permissions:
            database_permissions = self._copy_database_permissions(precomputed_db_permissions.get(login_name) or {})
        else:
            database_permissions = self._copy_database_permissions(self._get_database_permissions(connection, login_name))

        permissions = {
            "server_roles": server_roles,
            "server_permissions": server_permissions,
            "database_roles": database_roles,
            "database_permissions": database_permissions,
            "type_specific": {},
        }
        return permissions

    @staticmethod
    def _deduplicate_preserve_order(values: Sequence[Any] | None) -> List[Any]:
        if not values:
            return []
        seen: set[Any] = set()
        result: List[Any] = []
        for value in values:
            if value is None:
                continue
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _copy_database_permissions(self, data: Dict[str, Any] | None) -> Dict[str, Any]:
        if not data:
            return {}

        copied: Dict[str, Any] = {}
        for db_name, perms in data.items():
            if not db_name:
                continue
            if isinstance(perms, dict):
                db_entry: Dict[str, Any] = {
                    "database": self._deduplicate_preserve_order(perms.get("database", [])),
                    "schema": {},
                    "table": {},
                }
                schema_map = perms.get("schema") or {}
                db_entry["schema"] = {
                    schema_name: self._deduplicate_preserve_order(values)
                    for schema_name, values in schema_map.items()
                    if schema_name
                }
                table_map = perms.get("table") or {}
                db_entry["table"] = {
                    table_name: self._deduplicate_preserve_order(values)
                    for table_name, values in table_map.items()
                    if table_name
                }
                column_map = perms.get("column") or {}
                if column_map:
                    db_entry["column"] = {
                        column_name: self._deduplicate_preserve_order(values)
                        for column_name, values in column_map.items()
                        if column_name
                    }
                copied[db_name] = db_entry
            elif isinstance(perms, list):
                copied[db_name] = self._deduplicate_preserve_order(perms)
        return copied

    def _get_server_roles(self, connection: Any, login_name: str) -> List[str]:
        sql = """
            SELECT DISTINCT role.name
            FROM sys.server_role_members rm
            JOIN sys.server_principals role ON rm.role_principal_id = role.principal_id
            JOIN sys.server_principals member ON rm.member_principal_id = member.principal_id
            WHERE member.name = %s
        """
        rows = connection.execute_query(sql, (login_name,))
        return [row[0] for row in rows if row and row[0]]

    def _get_server_permissions(self, connection: Any, login_name: str) -> List[str]:
        sql = """
            SELECT DISTINCT permission_name
            FROM sys.server_permissions perm
            JOIN sys.server_principals sp ON perm.grantee_principal_id = sp.principal_id
            WHERE sp.name = %s
        """
        rows = connection.execute_query(sql, (login_name,))
        return [row[0] for row in rows if row and row[0]]

    def _get_server_roles_bulk(self, connection: Any, usernames: Sequence[str]) -> Dict[str, List[str]]:
        normalized = [name for name in usernames if name]
        if not normalized:
            return {}

        placeholders = ", ".join(["%s"] * len(normalized))
        sql = f"""
            SELECT member.name AS login_name, role.name AS role_name
            FROM sys.server_role_members rm
            JOIN sys.server_principals role ON rm.role_principal_id = role.principal_id
            JOIN sys.server_principals member ON rm.member_principal_id = member.principal_id
            WHERE member.name IN ({placeholders})
        """
        rows = connection.execute_query(sql, tuple(normalized))
        result: Dict[str, List[str]] = {}
        for login_name, role_name in rows:
            if not login_name or not role_name:
                continue
            result.setdefault(login_name, []).append(role_name)
        for login_name, roles in result.items():
            result[login_name] = self._deduplicate_preserve_order(roles)
        return result

    def _get_server_permissions_bulk(self, connection: Any, usernames: Sequence[str]) -> Dict[str, List[str]]:
        normalized = [name for name in usernames if name]
        if not normalized:
            return {}

        placeholders = ", ".join(["%s"] * len(normalized))
        sql = f"""
            SELECT sp.name AS login_name, perm.permission_name
            FROM sys.server_permissions perm
            JOIN sys.server_principals sp ON perm.grantee_principal_id = sp.principal_id
            WHERE sp.name IN ({placeholders})
        """
        rows = connection.execute_query(sql, tuple(normalized))
        result: Dict[str, List[str]] = {}
        for login_name, permission_name in rows:
            if not login_name or not permission_name:
                continue
            result.setdefault(login_name, []).append(permission_name)
        for login_name, permissions in result.items():
            result[login_name] = self._deduplicate_preserve_order(permissions)
        return result

    def _get_database_roles(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
        sql = """
            SELECT dp.name AS database_name, mp.name AS role_name
            FROM sys.server_principals sp
            JOIN sys.database_principals mp ON mp.sid = sp.sid
            JOIN sys.databases dp ON dp.owner_sid = mp.sid
            WHERE sp.name = %s
        """
        rows = connection.execute_query(sql, (login_name,))
        db_roles: Dict[str, List[str]] = {}
        for row in rows:
            database = row[0]
            role = row[1]
            if not database or not role:
                continue
            db_roles.setdefault(database, []).append(role)
        return db_roles

    def _get_database_permissions(self, connection: Any, login_name: str) -> Dict[str, List[str]]:
        sql = """
            DECLARE @login NVARCHAR(256);
            SET @login = %s;

            IF OBJECT_ID('tempdb..#perm_table') IS NOT NULL
                DROP TABLE #perm_table;

            CREATE TABLE #perm_table (
                database_name NVARCHAR(128),
                permission_name NVARCHAR(128)
            );

            DECLARE @db NVARCHAR(128);
            DECLARE db_cursor CURSOR FAST_FORWARD FOR
                SELECT name FROM sys.databases WHERE state_desc = 'ONLINE';

            OPEN db_cursor;
            FETCH NEXT FROM db_cursor INTO @db;

            WHILE @@FETCH_STATUS = 0
            BEGIN
                DECLARE @sql NVARCHAR(MAX) = N'
                    INSERT INTO #perm_table (database_name, permission_name)
                    SELECT N''' + @db + N''', perm.permission_name
                    FROM ' + QUOTENAME(@db) + N'.sys.database_permissions perm
                    JOIN ' + QUOTENAME(@db) + N'.sys.database_principals dp
                        ON perm.grantee_principal_id = dp.principal_id
                    WHERE dp.name = @login';

                BEGIN TRY
                    EXEC sp_executesql @sql, N'@login NVARCHAR(256)', @login=@login;
                END TRY
                BEGIN CATCH
                    PRINT ERROR_MESSAGE();
                END CATCH

                FETCH NEXT FROM db_cursor INTO @db;
            END

            CLOSE db_cursor;
            DEALLOCATE db_cursor;

            SELECT database_name, permission_name FROM #perm_table;
        """

        rows: List[tuple[Any, Any]] = []
        try:
            rows = connection.execute_query(sql, (login_name,))
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_sqlserver_db_permissions_failed",
                module="sqlserver_account_adapter",
                login=login_name,
                error=str(exc),
                exc_info=True,
            )
        db_perms: Dict[str, List[str]] = {}
        for row in rows:
            database = row[0]
            permission = row[1]
            if not database or not permission:
                continue
            db_perms.setdefault(database, []).append(permission)
        return db_perms

    def _get_all_users_database_permissions_batch_optimized(
        self,
        connection: Any,
        usernames: Sequence[str],
    ) -> Dict[str, Dict[str, Any]]:
        usernames = [name for name in usernames if name]
        if not usernames:
            return {}

        start_time = time.perf_counter()
        try:
            databases_sql = """
                SELECT name
                FROM sys.databases
                WHERE state = 0
                  AND HAS_DBACCESS(name) = 1
                ORDER BY name
            """
            database_rows = connection.execute_query(databases_sql)
            database_list = [row[0] for row in database_rows if row and row[0]]
            if not database_list:
                return {}

            unique_usernames = list(dict.fromkeys(usernames))
            placeholders = ", ".join(["%s"] * len(unique_usernames))
            login_sids_sql = f"""
                SELECT name, sid
                FROM sys.server_principals
                WHERE name IN ({placeholders})
                  AND type IN ('S', 'U', 'G')
            """
            login_rows = connection.execute_query(login_sids_sql, tuple(unique_usernames))
            sid_to_logins: Dict[bytes, List[str]] = {}
            for login_name, raw_sid in login_rows:
                normalized_sid = self._normalize_sid(raw_sid)
                if not login_name or normalized_sid is None:
                    continue
                sid_to_logins.setdefault(normalized_sid, []).append(login_name)

            if not sid_to_logins:
                return {}

            sid_literals = [
                literal for sid in sid_to_logins for literal in [self._sid_to_hex_literal(sid)] if literal
            ]
            if not sid_literals:
                return {}
            sid_filter = ", ".join(sid_literals)

            principals_parts: List[str] = []
            roles_parts: List[str] = []
            perms_parts: List[str] = []

            for db in database_list:
                quoted_db = self._quote_identifier(db)
                principals_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           name COLLATE SQL_Latin1_General_CP1_CI_AS AS user_name,
                           principal_id,
                           sid
                    FROM {quoted_db}.sys.database_principals
                    WHERE type IN ('S', 'U', 'G')
                      AND name != 'dbo'
                      AND sid IN ({sid_filter})
                    """
                )

                roles_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           role.name COLLATE SQL_Latin1_General_CP1_CI_AS AS role_name,
                           member.principal_id AS member_principal_id
                    FROM {quoted_db}.sys.database_role_members drm
                    JOIN {quoted_db}.sys.database_principals role
                      ON drm.role_principal_id = role.principal_id
                    JOIN {quoted_db}.sys.database_principals member
                      ON drm.member_principal_id = member.principal_id
                    WHERE member.sid IN ({sid_filter})
                    """
                )

                perms_parts.append(
                    f"""
                    SELECT '{db}' AS db_name,
                           perm.permission_name COLLATE SQL_Latin1_General_CP1_CI_AS AS permission_name,
                           perm.grantee_principal_id,
                           perm.major_id,
                           perm.minor_id,
                           CASE
                               WHEN perm.class_desc = 'DATABASE' THEN 'DATABASE'
                               WHEN perm.class_desc = 'SCHEMA' THEN 'SCHEMA'
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id = 0 THEN 'OBJECT'
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id > 0 THEN 'COLUMN'
                               ELSE perm.class_desc
                           END AS permission_scope,
                           CASE
                               WHEN perm.class_desc = 'SCHEMA' THEN SCHEMA_NAME(perm.major_id)
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' THEN OBJECT_SCHEMA_NAME(perm.major_id)
                               ELSE NULL
                           END AS schema_name,
                           CASE
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' THEN OBJECT_NAME(perm.major_id)
                               ELSE NULL
                           END AS object_name,
                           CASE
                               WHEN perm.class_desc = 'OBJECT_OR_COLUMN' AND perm.minor_id > 0 THEN COL_NAME(perm.major_id, perm.minor_id)
                               ELSE NULL
                           END AS column_name
                    FROM {quoted_db}.sys.database_permissions perm
                    JOIN {quoted_db}.sys.database_principals dp
                      ON perm.grantee_principal_id = dp.principal_id
                    WHERE perm.state = 'G'
                      AND dp.sid IN ({sid_filter})
                    """
                )

            principals_sql = " UNION ALL ".join(principals_parts)
            roles_sql = " UNION ALL ".join(roles_parts)
            perms_sql = " UNION ALL ".join(perms_parts)

            principal_rows = connection.execute_query(principals_sql)
            role_rows = connection.execute_query(roles_sql)
            permission_rows = connection.execute_query(perms_sql)

            principal_lookup: Dict[str, Dict[int, List[str]]] = {}
            for db_name, _, principal_id, sid in principal_rows:
                normalized_sid = self._normalize_sid(sid)
                if not db_name or principal_id is None or normalized_sid is None:
                    continue
                login_names = sid_to_logins.get(normalized_sid)
                if not login_names:
                    continue
                db_entry = principal_lookup.setdefault(db_name, {})
                db_entry.setdefault(principal_id, [])
                for login_name in login_names:
                    if login_name not in db_entry[principal_id]:
                        db_entry[principal_id].append(login_name)

            result: Dict[str, Dict[str, Any]] = {
                login: {"roles": {}, "permissions": {}}
                for login in unique_usernames
            }

            for db_name, role_name, member_principal_id in role_rows:
                if not db_name or not role_name or member_principal_id is None:
                    continue
                login_names = principal_lookup.get(db_name, {}).get(member_principal_id)
                if not login_names:
                    continue
                for login_name in login_names:
                    roles = result.setdefault(login_name, {}).setdefault("roles", {})
                    role_list = roles.setdefault(db_name, [])
                    if role_name not in role_list:
                        role_list.append(role_name)

            for (
                db_name,
                permission_name,
                grantee_principal_id,
                major_id,
                minor_id,
                scope,
                schema_name,
                object_name,
                column_name,
            ) in permission_rows:
                if not db_name or not permission_name or grantee_principal_id is None:
                    continue
                login_names = principal_lookup.get(db_name, {}).get(grantee_principal_id)
                if not login_names:
                    continue
                for login_name in login_names:
                    permissions = result.setdefault(login_name, {}).setdefault("permissions", {})
                    db_entry = permissions.setdefault(
                        db_name,
                        {
                            "database": [],
                            "schema": {},
                            "table": {},
                            "column": {},
                        },
                    )
                    if scope == "DATABASE":
                        if permission_name not in db_entry["database"]:
                            db_entry["database"].append(permission_name)
                    elif scope == "SCHEMA" and schema_name:
                        schema_list = db_entry["schema"].setdefault(schema_name, [])
                        if permission_name not in schema_list:
                            schema_list.append(permission_name)
                    elif scope == "OBJECT" and object_name:
                        qualified_name = f"{schema_name}.{object_name}" if schema_name else object_name
                        table_list = db_entry["table"].setdefault(qualified_name, [])
                        if permission_name not in table_list:
                            table_list.append(permission_name)
                    elif scope == "COLUMN" and object_name and column_name:
                        qualified_name = f"{schema_name}.{object_name}" if schema_name else object_name
                        table_list = db_entry["table"].setdefault(qualified_name, [])
                        if permission_name not in table_list:
                            table_list.append(permission_name)
                        column_key = f"{qualified_name}.{column_name}"
                        column_list = db_entry["column"].setdefault(column_key, [])
                        if permission_name not in column_list:
                            column_list.append(permission_name)

            elapsed = time.perf_counter() - start_time
            self.logger.info(
                "sqlserver_batch_database_permissions_completed",
                module="sqlserver_account_adapter",
                user_count=len(unique_usernames),
                database_count=len(database_list),
                elapsed_time=f"{elapsed:.2f}s",
            )

            return result
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "sqlserver_batch_database_permissions_failed",
                module="sqlserver_account_adapter",
                error=str(exc),
                exc_info=True,
            )
            return {}

    @staticmethod
    def _normalize_sid(raw_sid: Any) -> bytes | None:
        if raw_sid is None:
            return None
        if isinstance(raw_sid, memoryview):
            return raw_sid.tobytes()
        if isinstance(raw_sid, bytearray):
            return bytes(raw_sid)
        if isinstance(raw_sid, bytes):
            return raw_sid
        return None

    @staticmethod
    def _sid_to_hex_literal(sid: bytes | None) -> str | None:
        if not sid:
            return None
        return "0x" + sid.hex()

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        safe_identifier = identifier.replace("]", "]]")
        return f"[{safe_identifier}]"


    # 缓存操作
    def clear_user_cache(self, instance: Instance, username: str) -> bool:
        try:
            return cache_manager.invalidate_user_cache(instance.id, username)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "clear_sqlserver_user_cache_failed",
                instance=instance.name,
                username=username,
                error=str(exc),
            )
            return False

    def clear_instance_cache(self, instance: Instance) -> bool:
        try:
            return cache_manager.invalidate_instance_cache(instance.id)
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "clear_sqlserver_instance_cache_failed",
                instance=instance.name,
                error=str(exc),
            )
            return False
