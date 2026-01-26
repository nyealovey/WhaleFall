"""SQL Server 数据库连接适配器."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

import pymssql  # type: ignore[import-not-found]

from app.core.types import DBAPICursor

from .base import (
    ConnectionAdapterError,
    DatabaseConnection,
    DBAPIConnection,
    QueryParams,
    QueryResult,
    get_default_schema,
)

SQLSERVER_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (pymssql.Error,)

SQLSERVER_CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
    *SQLSERVER_DRIVER_EXCEPTIONS,
)


if TYPE_CHECKING:
    from app.core.types import JsonValue
    from app.models.instance import Instance
else:
    Instance = Any
    JsonValue = Any


class SQLServerConnection(DatabaseConnection):
    """SQL Server 数据库连接."""

    def __init__(self, instance: Instance) -> None:
        """初始化 SQL Server 连接适配器.

        Args:
            instance: 数据库实例对象.

        """
        super().__init__(instance)
        self.driver_type: str | None = None

    def connect(self) -> bool:
        """建立 SQL Server 连接(当前仅支持 pymssql).

        Returns:
            bool: 连接成功返回 True,失败返回 False.

        """
        password = self.instance.credential.get_plain_password() if self.instance.credential else ""
        username = self.instance.credential.username if self.instance.credential else ""
        database_name = self.instance.database_name or get_default_schema("sqlserver") or "master"

        try:
            success = self._try_pymssql_connection(username, password, database_name)
        except SQLSERVER_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.exception(
                "SQL Server连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="SQL Server",
                host=self.instance.host,
                port=self.instance.port,
                database=database_name,
                username=username,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return False
        return success

    def _try_pymssql_connection(self, username: str, password: str, database_name: str) -> bool:
        """使用 pymssql 尝试连接 SQL Server.

        Args:
            username: 登录用户名.
            password: 密码.
            database_name: 目标数据库.

        Returns:
            bool: 连接成功返回 True.

        """
        try:
            self.connection = pymssql.connect(
                server=self.instance.host,
                port=self.instance.port,
                user=username,
                password=password,
                database=database_name,
                timeout=300,
                login_timeout=20,
                tds_version="7.2",
            )
        except SQLSERVER_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.exception(
                "SQL Server连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="SQL Server",
                host=self.instance.host,
                port=self.instance.port,
                database=database_name,
                username=username,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return False
        else:
            self.is_connected = True
            self.driver_type = "pymssql"
            return True

    def disconnect(self) -> None:
        """断开 SQL Server 连接并清理状态.

        Returns:
            None

        """
        if self.connection:
            conn = cast(DBAPIConnection, self.connection)
            try:
                conn.close()
            except SQLSERVER_CONNECTION_EXCEPTIONS as exc:
                self.db_logger.warning(
                    "SQL Server断开连接出现异常",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="SQL Server",
                    error=str(exc),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, JsonValue]:
        """测试连接并返回版本信息."""
        try:
            if not self.connect():
                result: dict[str, JsonValue] = {
                    "success": False,
                    "message": f"SQL Server连接失败 (主机: {self.instance.host}:{self.instance.port})",
                    "error": "无法建立连接",
                }
            else:
                version = self.get_version()
                message = (
                    f"SQL Server连接成功 (主机: {self.instance.host}:{self.instance.port}, "
                    f"版本: {version or '未知'})"
                )
                result = {
                    "success": True,
                    "message": message,
                    "database_version": version,
                }
        except SQLSERVER_CONNECTION_EXCEPTIONS as exc:
            result = {
                "success": False,
                "message": f"SQL Server连接测试失败 (主机: {self.instance.host}:{self.instance.port})",
                "error": str(exc),
            }
        finally:
            self.disconnect()
        return result

    def execute_query(
        self,
        query: str,
        params: QueryParams = None,
    ) -> QueryResult:
        """执行 SQL 查询并返回 `fetchall` 结果.

        Args:
            query: SQL 语句.
            params: 查询参数.

        Returns:
            QueryResult: `fetchall` 的结果.

        """
        if not self.is_connected and not self.connect():
            msg = "无法建立数据库连接"
            raise ConnectionAdapterError(msg)

        conn = cast(DBAPIConnection, self.connection)
        cursor = cast(DBAPICursor, conn.cursor())
        try:
            bound_params: Sequence[JsonValue] | Mapping[str, JsonValue]
            if isinstance(params, Mapping):
                bound_params = params
            elif params is None:
                bound_params = ()
            else:
                bound_params = tuple(params)
            cursor.execute(query, bound_params)
            rows = cast("Sequence[Sequence[JsonValue]]", cursor.fetchall())
            return list(rows)
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """查询 SQL Server 版本字符串.

        Returns:
            str | None: 成功时返回版本字符串.

        """
        try:
            result = self.execute_query("SELECT @@VERSION")
        except SQLSERVER_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.warning(
                "SQL Server版本查询失败",
                module="connection",
                action="get_version",
                instance_id=self.instance.id,
                db_type="SQLServer",
                fallback=True,
                fallback_reason="DB_VERSION_QUERY_FAILED",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return None
        if result:
            version_val = result[0][0] if result[0] else None
            return version_val if isinstance(version_val, str) else None
        return None
