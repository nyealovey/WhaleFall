"""PostgreSQL 数据库连接适配器."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, cast

import psycopg  # type: ignore[import-not-found]

if TYPE_CHECKING:
    from app.core.types import JsonValue
else:
    JsonValue = Any

from app.core.types import DBAPICursor

from .base import (
    ConnectionAdapterError,
    DatabaseConnection,
    DBAPIConnection,
    QueryParams,
    QueryResult,
    get_default_schema,
)

POSTGRES_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (psycopg.Error,)

POSTGRES_CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
    *POSTGRES_DRIVER_EXCEPTIONS,
)


class PostgreSQLConnection(DatabaseConnection):
    """PostgreSQL 数据库连接."""

    def connect(self) -> bool:
        """建立 PostgreSQL 连接.

        Returns:
            bool: 连接成功返回 True,否则 False.

        """
        password = self.instance.credential.get_plain_password() if self.instance.credential else ""

        try:
            self.connection = psycopg.connect(
                host=self.instance.host,
                port=self.instance.port,
                dbname=self.instance.database_name or get_default_schema("postgresql") or "postgres",
                user=(self.instance.credential.username if self.instance.credential else ""),
                password=password,
                connect_timeout=20,
                options="-c statement_timeout=300000",
            )
        except POSTGRES_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.exception(
                "PostgreSQL连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="PostgreSQL",
                exception=str(exc),
            )
            return False
        else:
            self.is_connected = True
            return True

    def disconnect(self) -> None:
        """关闭 PostgreSQL 连接并复位状态.

        Returns:
            None

        """
        if self.connection:
            conn = cast(DBAPIConnection, self.connection)
            try:
                conn.close()
            except POSTGRES_CONNECTION_EXCEPTIONS as exc:
                self.db_logger.exception(
                    "PostgreSQL断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="PostgreSQL",
                    exception=str(exc),
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
                    f"PostgreSQL连接成功 (主机: {self.instance.host}:{self.instance.port}, "
                    f"版本: {version or '未知'})"
                )
                result = {
                    "success": True,
                    "message": message,
                    "database_version": version,
                }
        except POSTGRES_CONNECTION_EXCEPTIONS as exc:
            result = {"success": False, "error": str(exc)}
        finally:
            self.disconnect()
        return result

    def execute_query(
        self,
        query: str,
        params: QueryParams = None,
    ) -> QueryResult:
        """执行 SQL 查询并返回所有结果.

        Args:
            query: SQL 语句.
            params: 可选绑定参数.

        Returns:
            QueryResult: `fetchall` 的返回值.

        """
        if not self.is_connected and not self.connect():
            msg = "无法建立数据库连接"
            raise ConnectionAdapterError(msg)

        conn = cast(DBAPIConnection, self.connection)
        cursor = cast(DBAPICursor, conn.cursor())
        try:
            bound_params: Sequence[JsonValue] | Mapping[str, JsonValue]
            bound_params = params if isinstance(params, Mapping) else tuple(params or [])
            cursor.execute(query, bound_params)
            rows = cast("Sequence[Sequence[JsonValue]]", cursor.fetchall())
            return list(rows)
        finally:
            cursor.close()

    def get_version(self) -> str | None:
        """查询数据库版本字符串.

        Returns:
            str | None: 版本号,失败返回 None.

        """
        try:
            result = self.execute_query("SELECT version()")
        except POSTGRES_CONNECTION_EXCEPTIONS:
            return None
        if result:
            version_val = result[0][0] if result[0] else None
            return version_val if isinstance(version_val, str) else None
        return None
