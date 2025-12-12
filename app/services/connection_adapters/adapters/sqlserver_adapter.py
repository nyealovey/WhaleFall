"""SQL Server 数据库连接适配器."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from app.utils.sqlserver_connection_utils import sqlserver_connection_utils

try:  # pragma: no cover - 运行环境可能未安装 pymssql
    import pymssql  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    pymssql = None  # type: ignore[assignment]

from .base import (
    ConnectionAdapterError,
    DatabaseConnection,
    QueryParams,
    QueryResult,
    get_default_schema,
)

if pymssql:
    SQLSERVER_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (pymssql.Error,)
else:  # pragma: no cover - optional dependency
    SQLSERVER_DRIVER_EXCEPTIONS = ()

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
    from app.models.instance import Instance
    from app.types import JsonValue
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
        if not pymssql:
            self.db_logger.exception(
                "pymssql模块未安装",
                module="connection",
                instance_id=self.instance.id,
                db_type="SQL Server",
            )
            return False

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
            diagnosis = sqlserver_connection_utils.diagnose_connection_error(
                str(exc),
                self.instance.host,
                self.instance.port,
            )
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
                diagnosis=diagnosis,
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
            try:
                self.connection.close()
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
                result: dict[str, JsonValue] = {"success": False, "error": "无法建立连接"}
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
            result = {"success": False, "error": str(exc)}
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

        cursor = self.connection.cursor()
        try:
            bound_params: Sequence[JsonValue] | Mapping[str, JsonValue]
            bound_params = params if isinstance(params, Mapping) else tuple(params or [])
            cursor.execute(query, bound_params)
            rows = cursor.fetchall()
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
        except SQLSERVER_CONNECTION_EXCEPTIONS:
            return None
        if result:
            return result[0][0]
        return None
