"""MySQL 数据库连接适配器."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.types import JsonValue
else:
    JsonValue = Any

try:  # pragma: no cover - 运行环境可能未安装 pymysql
    import pymysql  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    pymysql = None  # type: ignore[assignment]

from .base import (
    ConnectionAdapterError,
    DatabaseConnection,
    QueryParams,
    QueryResult,
    get_default_schema,
)

if pymysql:
    MYSQL_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (pymysql.MySQLError,)
else:  # pragma: no cover - optional dependency
    MYSQL_DRIVER_EXCEPTIONS = ()

MYSQL_CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
    *MYSQL_DRIVER_EXCEPTIONS,
)


class MySQLConnection(DatabaseConnection):
    """MySQL 数据库连接."""

    def connect(self) -> bool:
        """建立 MySQL 连接并缓存连接对象.

        Returns:
            bool: 连接成功返回 True,失败返回 False.

        """
        if not pymysql:
            self.db_logger.exception(
                "pymysql模块未安装",
                module="connection",
                instance_id=self.instance.id,
                db_type="MySQL",
            )
            return False

        password = self.instance.credential.get_plain_password() if self.instance.credential else ""

        try:
            self.connection = pymysql.connect(
                host=self.instance.host,
                port=self.instance.port,
                database=self.instance.database_name or get_default_schema("mysql"),
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                charset="utf8mb4",
                autocommit=True,
                connect_timeout=20,
                read_timeout=300,
                write_timeout=300,
                sql_mode="TRADITIONAL",
            )
        except MYSQL_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.exception(
                "MySQL连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="MySQL",
                error=str(exc),
            )
            return False
        else:
            self.is_connected = True
            return True

    def disconnect(self) -> None:
        """关闭当前连接并复位状态标识.

        Returns:
            None

        """
        if self.connection:
            try:
                self.connection.close()
            except MYSQL_CONNECTION_EXCEPTIONS as exc:
                self.db_logger.exception(
                    "MySQL断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="MySQL",
                    error=str(exc),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, JsonValue]:
        """快速测试数据库连通性并返回版本信息."""
        try:
            if not self.connect():
                result: dict[str, JsonValue] = {"success": False, "error": "无法建立连接"}
            else:
                version = self.get_version()
                message = (
                    f"MySQL连接成功 (主机: {self.instance.host}:{self.instance.port}, "
                    f"版本: {version or '未知'})"
                )
                result = {
                    "success": True,
                    "message": message,
                    "database_version": version,
                }
        except MYSQL_CONNECTION_EXCEPTIONS as exc:
            result = {"success": False, "error": str(exc)}
        finally:
            self.disconnect()
        return result

    def execute_query(
        self,
        query: str,
        params: QueryParams = None,
    ) -> QueryResult:
        """执行 SQL 查询并返回全部结果.

        Args:
            query: 待执行的 SQL 语句.
            params: 绑定参数(序列或命名参数).

        Returns:
            QueryResult: pymysql `fetchall` 的结果.

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
        """查询数据库版本.

        Returns:
            str | None: 成功时返回版本字符串,否则 None.

        """
        try:
            result = self.execute_query("SELECT VERSION()")
        except MYSQL_CONNECTION_EXCEPTIONS:
            return None
        if result:
            return result[0][0]
        return None
