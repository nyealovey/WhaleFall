"""Oracle 账户同步适配器(两阶段版)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from app.constants import DatabaseType
from app.services.accounts_sync.accounts_sync_filters import DatabaseFilterManager
from app.services.accounts_sync.adapters.base_adapter import BaseAccountAdapter
from app.services.connection_adapters.adapters.base import ConnectionAdapterError
from app.utils.structlog_config import get_sync_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.models.instance import Instance
    from app.types import JsonDict, PermissionSnapshot, RawAccount, RemoteAccount
else:
    Instance = Any
    JsonDict = dict[str, Any]
    PermissionSnapshot = dict[str, Any]
    RawAccount = dict[str, Any]
    RemoteAccount = dict[str, Any]

try:  # pragma: no cover - 运行环境可能未安装 oracledb
    import oracledb  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - optional dependency
    oracledb = None  # type: ignore[assignment]

if oracledb:
    ORACLE_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (oracledb.Error,)
else:  # pragma: no cover - optional dependency
    ORACLE_DRIVER_EXCEPTIONS = ()

ORACLE_ADAPTER_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    LookupError,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    ConnectionError,
    TimeoutError,
    *ORACLE_DRIVER_EXCEPTIONS,
)


class OracleAccountAdapter(BaseAccountAdapter):
    """Oracle 账户同步适配器.

    实现 Oracle 数据库的账户查询和权限采集功能.
    通过 dba_users、dba_role_privs、dba_sys_privs 等视图采集用户信息和权限.

    Attributes:
        logger: 同步日志记录器.
        filter_manager: 数据库过滤管理器.

    Example:
        >>> adapter = OracleAccountAdapter()
        >>> accounts = adapter.fetch_accounts(instance, connection)
        >>> enriched = adapter.enrich_permissions(instance, connection, accounts)

    """

    def __init__(self) -> None:
        """初始化 Oracle 适配器,配置日志与过滤管理器."""
        self.logger = get_sync_logger()
        self.filter_manager = DatabaseFilterManager()

    def _fetch_raw_accounts(self, instance: Instance, connection: object) -> list[RawAccount]:
        """拉取 Oracle 原始账户信息.

        从 dba_users 视图中查询用户基本信息.

        Args:
            instance: 实例对象.
            connection: Oracle 数据库连接对象.

        Returns:
            原始账户信息列表,每个元素包含用户名、账户状态、默认表空间等.

        """
        try:
            users = self._fetch_users(connection)
        except ORACLE_ADAPTER_EXCEPTIONS as exc:
            self.logger.exception(
                "fetch_oracle_accounts_failed",
                module="oracle_account_adapter",
                instance=instance.name,
                error=str(exc),
            )
            return []
        else:
            accounts: list[RawAccount] = []
            for user in users:
                username = user["username"]
                account_status = user["account_status"]
                is_locked = account_status.upper() != "OPEN"
                accounts.append(
                    {
                        "username": username,
                        "is_superuser": user.get("is_dba", False),
                        "is_locked": is_locked,
                        "permissions": {
                            "type_specific": {
                                "account_status": account_status,
                                "default_tablespace": user.get("default_tablespace"),
                            },
                        },
                    },
                )
            self.logger.info(
                "fetch_oracle_accounts_success",
                module="oracle_account_adapter",
                instance=instance.name,
                account_count=len(accounts),
            )
            return accounts

    def _normalize_account(self, instance: Instance, account: RawAccount) -> RemoteAccount:
        """规范化 Oracle 账户信息.

        将原始账户信息转换为统一格式.

        Args:
            instance: 实例对象.
            account: 原始账户信息字典.

        Returns:
            规范化后的账户信息字典.

        """
        _ = instance
        permissions = cast("PermissionSnapshot", account.get("permissions") or {})
        type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
        account_status = type_specific.get("account_status")
        is_locked = bool(account.get("is_locked", False))
        if isinstance(account_status, str):
            is_locked = account_status.upper() != "OPEN"
        return {
            "username": account["username"],
            "display_name": account["username"],
            "db_type": DatabaseType.ORACLE,
            "is_superuser": account.get("is_superuser", False),
            "is_locked": is_locked,
            "is_active": True,
            "permissions": {
                "oracle_roles": permissions.get("oracle_roles", []),
                "system_privileges": permissions.get("system_privileges", []),
                "tablespace_quotas": permissions.get("tablespace_quotas", {}),
                "type_specific": permissions.get("type_specific", {}),
            },
        }

    # ------------------------------------------------------------------
    def _fetch_users(self, connection: object) -> list[RawAccount]:
        """读取 Oracle 用户列表.

        Args:
            connection: Oracle 数据库连接对象.

        Returns:
            list[RawAccount]: 包含用户名、状态及默认表空间的用户集合.

        """
        filter_rules = self.filter_manager.get_filter_rules("oracle")
        exclude_users = cast("list[str]", filter_rules.get("exclude_users", []))
        placeholders = ",".join([f":{i}" for i in range(1, len(exclude_users) + 1)]) or "''"

        sql = (
            "SELECT username, account_status, default_tablespace "
            "FROM dba_users "
            "WHERE username NOT IN ("
            + placeholders
            + ")"
        )
        params = {f":{i+1}": user for i, user in enumerate(exclude_users)}
        rows = connection.execute_query(sql, params)
        return [
            {
                "username": row[0],
                "account_status": row[1],
                "default_tablespace": row[2],
                "is_dba": row[0] == "SYS",
            }
            for row in rows
        ]

    def _get_user_permissions(self, connection: object, username: str) -> PermissionSnapshot:
        """查询单个用户的权限快照.

        Args:
            connection: Oracle 数据库连接对象.
            username: 目标用户名.

        Returns:
            PermissionSnapshot: 角色、系统权限与表空间配额等信息.

        """
        return {
            "oracle_roles": self._get_roles(connection, username),
            "system_privileges": self._get_system_privileges(connection, username),
            "tablespace_quotas": self._get_tablespace_privileges(connection, username),
            "type_specific": {},
        }

    def enrich_permissions(
        self,
        instance: Instance,
        connection: object,
        accounts: list[RemoteAccount],
        *,
        usernames: Sequence[str] | None = None,
    ) -> list[RemoteAccount]:
        """丰富 Oracle 账户的权限信息.

        为指定账户查询详细的权限信息,包括角色、系统权限、表空间配额等.

        Args:
            instance: 实例对象.
            connection: Oracle 数据库连接对象.
            accounts: 账户信息列表.
            usernames: 可选的目标用户名列表.

        Returns:
            丰富后的账户信息列表.

        """
        target_usernames = {account["username"] for account in accounts} if usernames is None else set(usernames)
        if not target_usernames:
            return accounts

        processed = 0
        for account in accounts:
            username = account.get("username")
            if not username or username not in target_usernames:
                continue
            processed += 1
            try:
                permissions = self._get_user_permissions(connection, username)
                type_specific = cast("JsonDict", permissions.setdefault("type_specific", {}))
                account["permissions"] = permissions
                account_status = type_specific.get("account_status")
                if isinstance(account_status, str):
                    account["is_locked"] = account_status.upper() != "OPEN"
            except ORACLE_ADAPTER_EXCEPTIONS as exc:
                self.logger.exception(
                    "fetch_oracle_permissions_failed",
                    module="oracle_account_adapter",
                    instance=instance.name,
                    username=username,
                    error=str(exc),
                )
                account.setdefault("permissions", {}).setdefault("errors", []).append(str(exc))

        self.logger.info(
            "fetch_oracle_permissions_completed",
            module="oracle_account_adapter",
            instance=instance.name,
            processed_accounts=processed,
        )
        return accounts

    def _get_roles(self, connection: object, username: str) -> list[str]:
        """查询用户拥有的角色.

        Args:
            connection: Oracle 数据库连接.
            username: 目标用户名.

        Returns:
            list[str]: 已授予的角色名称列表.

        """
        sql = "SELECT granted_role FROM dba_role_privs WHERE grantee = :1"
        rows = connection.execute_query(sql, {":1": username})
        return [row[0] for row in rows if row and row[0]]

    def _get_system_privileges(self, connection: object, username: str) -> list[str]:
        """查询用户拥有的系统权限.

        Args:
            connection: Oracle 数据库连接.
            username: 目标用户名.

        Returns:
            list[str]: 系统权限名称列表.

        """
        sql = "SELECT privilege FROM dba_sys_privs WHERE grantee = :1"
        rows = connection.execute_query(sql, {":1": username})
        return [row[0] for row in rows if row and row[0]]

    def _get_tablespace_privileges(self, connection: object, username: str) -> dict[str, JsonDict]:
        """查询用户的表空间配额信息.

        从 dba_ts_quotas 视图中查询用户在各表空间的配额和使用情况.
        兼容 Oracle 11g 及以上版本.

        Args:
            connection: Oracle 数据库连接对象.
            username: 用户名.

        Returns:
            表空间配额字典,键为表空间名称,值包含配额和已使用空间.

        """
        sql = """
            SELECT
                tablespace_name,
                CASE
                    WHEN max_bytes = -1 THEN 'UNLIMITED'
                    ELSE TO_CHAR(max_bytes / 1024 / 1024) || ' MB'
                END AS quota,
                bytes / 1024 / 1024 AS used_mb
            FROM dba_ts_quotas
            WHERE username = :1
        """
        rows = connection.execute_query(sql, {":1": username})
        quotas: dict[str, JsonDict] = {}
        for row in rows:
            tablespace = row[0]
            quota = row[1]
            used_mb = float(row[2]) if row[2] else 0
            if not tablespace:
                continue
            quotas[tablespace] = {
                "quota": quota,
                "used_mb": round(used_mb, 2),
            }
        return quotas
