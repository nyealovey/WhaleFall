"""Oracle 数据库连接适配器."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import oracledb  # type: ignore[import-not-found]

from .base import ConnectionAdapterError, DatabaseConnection, QueryResult
from app.types import DBAPICursor, DBAPIConnection

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

ORACLE_DRIVER_EXCEPTIONS: tuple[type[BaseException], ...] = (oracledb.Error,)

ORACLE_CONNECTION_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionAdapterError,
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
    *ORACLE_DRIVER_EXCEPTIONS,
)


class OracleConnection(DatabaseConnection):
    """Oracle 数据库连接."""

    def connect(self) -> bool:
        """建立 Oracle 连接并在必要时初始化客户端.

        Returns:
            bool: 连接成功返回 True,失败返回 False.

        """
        username_for_connection = None
        try:
            password = self.instance.credential.get_plain_password() if self.instance.credential else ""
            username = self.instance.credential.username if self.instance.credential else ""
            username_for_connection = username.split("/")[0] if "/" in username else username
            host = self.instance.host
            port = self.instance.port
            service_name = self.instance.database_name or "ORCL"
            dsn = (
                "(DESCRIPTION="
                f"(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))"
                f"(CONNECT_DATA=(SERVICE_NAME={service_name})))"
            )

            is_thin = False
            if hasattr(oracledb, "is_thin"):
                try:
                    is_thin = bool(oracledb.is_thin())  # type: ignore[call-arg]
                except Exception:  # pragma: no cover - 防御性
                    is_thin = False
            if not is_thin:
                try:
                    candidate_paths: list[Path] = []
                    env_lib_dir = os.getenv("ORACLE_CLIENT_LIB_DIR")
                    if env_lib_dir:
                        candidate_paths.append(Path(env_lib_dir))

                    oracle_home = os.getenv("ORACLE_HOME")
                    if oracle_home:
                        candidate_paths.append(Path(oracle_home) / "lib")

                    current_dir = Path(__file__).resolve().parents[2]
                    candidate_paths.append(current_dir / "oracle_client" / "lib")

                    lib_dir = next((path for path in candidate_paths if path and path.is_dir()), None)
                    if lib_dir:
                        oracledb.init_oracle_client(lib_dir=str(lib_dir))
                    else:
                        oracledb.init_oracle_client()
                except ORACLE_CONNECTION_EXCEPTIONS as init_error:
                    if "already been initialized" not in str(init_error).lower():
                        self.db_logger.warning(
                            "Oracle客户端初始化警告",
                            module="connection",
                            instance_id=self.instance.id,
                            error=str(init_error),
                        )

            self.connection = oracledb.connect(
                user=username_for_connection,
                password=password,
                dsn=dsn,
            )
            self.is_connected = True
            self.db_logger.info(
                "Oracle连接成功",
                module="connection",
                instance_id=self.instance.id,
                username=username_for_connection,
            )
        except ORACLE_CONNECTION_EXCEPTIONS as exc:
            self.db_logger.exception(
                "Oracle连接失败",
                module="connection",
                instance_id=self.instance.id,
                db_type="Oracle",
                host=self.instance.host,
                port=self.instance.port,
                username=username_for_connection if username_for_connection else "unknown",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return False
        else:
            return True

    def disconnect(self) -> None:
        """断开 Oracle 连接并清理句柄.

        Returns:
            None

        """
        if self.connection:
            try:
                connection_obj = self.connection
                if hasattr(connection_obj, "close"):
                    connection_obj.close()  # type: ignore[call-arg]
            except ORACLE_CONNECTION_EXCEPTIONS as exc:
                self.db_logger.exception(
                    "Oracle断开连接失败",
                    module="connection",
                    instance_id=self.instance.id,
                    db_type="Oracle",
                    exception=str(exc),
                )
            finally:
                self.connection = None
                self.is_connected = False

    def test_connection(self) -> dict[str, Any]:
        """测试 Oracle 连接并返回版本信息."""
        try:
            if not self.connect():
                result: dict[str, Any] = {"success": False, "error": "无法建立连接"}
            else:
                version = self.get_version()
                message = (
                    f"Oracle连接成功 (主机: {self.instance.host}:{self.instance.port}, "
                    f"版本: {version or '未知'})"
                )
                result = {
                    "success": True,
                    "message": message,
                    "database_version": version,
                }
        except ORACLE_CONNECTION_EXCEPTIONS as exc:
            result = {"success": False, "error": str(exc)}
        finally:
            self.disconnect()
        return result

    def execute_query(
        self, query: str, params: Sequence[object] | Mapping[str, object] | None = None,
    ) -> QueryResult:
        """执行 SQL 查询并返回全部行.

        Args:
            query: SQL 语句.
            params: 查询参数,可为 tuple 或 dict.

        Returns:
            list[tuple]: 游标 `fetchall` 的结果.

        """
        if not self.is_connected and not self.connect():
            msg = "无法建立数据库连接"
            raise ConnectionAdapterError(msg)

        conn = cast(DBAPIConnection, self.connection)
        cursor = cast(DBAPICursor, conn.cursor())
        try:
            cursor.execute(query, params or ())
            return cast(QueryResult, cursor.fetchall())
        finally:
            if hasattr(cursor, "close"):
                cursor.close()

    def get_version(self) -> str | None:
        """获取 Oracle 版本字符串.

        Returns:
            str | None: 版本号,获取失败返回 None.

        """
        try:
            result = self.execute_query("SELECT * FROM v$version WHERE rownum = 1")
        except ORACLE_CONNECTION_EXCEPTIONS:
            return None
        if result:
            first_value = result[0][0] if result[0] else None
            return cast(str | None, first_value if isinstance(first_value, str) else None)
        return None
