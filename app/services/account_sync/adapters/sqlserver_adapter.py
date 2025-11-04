"""SQL Server 账户同步适配器（两阶段版）。"""

from __future__ import annotations

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

        db_permissions_map = self._get_database_permissions_bulk(connection, list(target_usernames))
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
                    precomputed_db_permissions=db_permissions_map,
                )
                permissions.setdefault("type_specific", {})["is_disabled"] = account.get("attributes", {}).get(
                    "is_disabled", account.get("is_disabled", False)
                )
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
        precomputed_db_permissions: Dict[str, Dict[str, List[str]]] | None = None,
    ) -> Dict[str, Any]:
        permissions = {
            "server_roles": self._get_server_roles(connection, login_name),
            "server_permissions": self._get_server_permissions(connection, login_name),
            "database_roles": self._get_database_roles(connection, login_name),
            "database_permissions": (
                precomputed_db_permissions.get(login_name)
                if precomputed_db_permissions
                else self._get_database_permissions(connection, login_name)
            ),
            "type_specific": {},
        }
        return permissions

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

    def _get_database_permissions_bulk(
        self,
        connection: Any,
        usernames: Sequence[str],
    ) -> Dict[str, Dict[str, List[str]]]:
        usernames = sorted({name for name in usernames if name})
        if not usernames:
            return {}

        placeholders = ", ".join(["(%s)"] * len(usernames))
        sql = f"""
            IF OBJECT_ID('tempdb..#login_filter') IS NOT NULL
                DROP TABLE #login_filter;

            CREATE TABLE #login_filter (
                username NVARCHAR(256) PRIMARY KEY
            );

            INSERT INTO #login_filter (username)
            VALUES {placeholders};

            IF OBJECT_ID('tempdb..#perm_table') IS NOT NULL
                DROP TABLE #perm_table;

            CREATE TABLE #perm_table (
                login_name NVARCHAR(256),
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
                    INSERT INTO #perm_table (login_name, database_name, permission_name)
                    SELECT lf.username, N''' + @db + N''', perm.permission_name
                    FROM ' + QUOTENAME(@db) + N'.sys.database_permissions perm
                    JOIN ' + QUOTENAME(@db) + N'.sys.database_principals dp
                        ON perm.grantee_principal_id = dp.principal_id
                    JOIN #login_filter lf ON dp.name = lf.username';

                BEGIN TRY
                    EXEC (@sql);
                END TRY
                BEGIN CATCH
                    PRINT ERROR_MESSAGE();
                END CATCH

                FETCH NEXT FROM db_cursor INTO @db;
            END

            CLOSE db_cursor;
            DEALLOCATE db_cursor;

            SELECT login_name, database_name, permission_name FROM #perm_table;
        """

        rows: List[tuple[Any, Any, Any]] = []
        try:
            rows = connection.execute_query(sql, tuple(usernames))
        except Exception as exc:  # noqa: BLE001
            self.logger.error(
                "fetch_sqlserver_db_permissions_bulk_failed",
                module="sqlserver_account_adapter",
                logins=usernames,
                error=str(exc),
                exc_info=True,
            )
            return {}

        user_db_perms: Dict[str, Dict[str, List[str]]] = {}
        for login_name, database, permission in rows:
            if not login_name or not database or not permission:
                continue
            db_map = user_db_perms.setdefault(login_name, {})
            db_map.setdefault(database, []).append(permission)

        return user_db_perms

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
